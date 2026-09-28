import base64
import datetime
import hashlib
import hmac
import os
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

from Actions.bson_codec import ObjectId, decode, encode
from config import MONGO_DB, MONGO_PASSWORD, MONGO_PORT, MONGO_USER

# Kleiner MongoDB-Server fuer Mission 6 - ersetzt mongod, wenn keiner installiert ist.
# Der Schildgenerator verbindet sich mit mongodb://theship:theship1234@192.168.101.51:2021/theshipdb
# und liest dort das Dokument aus der Collection vacuum-energy.
#
# Spricht das MongoDB-Wire-Protokoll (OP_MSG und das alte OP_QUERY fuer den Handshake),
# Login mit SCRAM-SHA-256 / SCRAM-SHA-1 und die Befehle find, insert, update, delete, count/aggregate
# (+ was Treiber und mongosh beim Verbinden fragen). Die Daten werden in mongo_data.bson
# gespeichert und ueberleben so einen Neustart.
#
# Laeuft wie der MQTT-Server als EIGENER Prozess weiter, auch wenn main.py beendet wird.
# Log: mongo_server.log (mission_6 zeigt es mit an). Stoppen: pkill -f mongo_server.py

OP_REPLY, OP_QUERY, OP_MSG = 1, 2004, 2013
MAX_WIRE_VERSION = 17                                 # verhaelt sich wie MongoDB 6.0

DATA_FILE = Path(__file__).with_name("mongo_data.bson")
LOG_FILE = Path(__file__).with_name("mongo_server.log")

_data = {}                                            # {db: {collection: [dokumente]}}
_data_lock = threading.Lock()
_connection_ids = iter(range(1, 10 ** 9))
_logged_in = set()


class CommandError(Exception):
    def __init__(self, code, name, message):
        super().__init__(message)
        self.code, self.name = code, name


# --- Speicher ------------------------------------------------------------

def _load():
    global _data
    if DATA_FILE.exists():
        _data = decode(DATA_FILE.read_bytes())[0]


def _save():
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_bytes(encode(_data))
    tmp.replace(DATA_FILE)


def _collection(db, name, create=False):
    if create:
        return _data.setdefault(db, {}).setdefault(name, [])
    return _data.get(db, {}).get(name, [])


# --- Filter und Updates ----------------------------------------------------

def _get_field(document, path):
    value = document
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None, False
        value = value[part]
    return value, True


_ORDER = {
    "$gt": lambda a, b: a > b,
    "$gte": lambda a, b: a >= b,
    "$lt": lambda a, b: a < b,
    "$lte": lambda a, b: a <= b,
}


def _compare(value, found, condition):
    if not isinstance(condition, dict) or not any(k.startswith("$") for k in condition):
        return found and value == condition
    for op, expected in condition.items():
        if op == "$eq" and not (found and value == expected):
            return False
        if op == "$ne" and found and value == expected:
            return False
        if op == "$in" and not (found and value in expected):
            return False
        if op == "$nin" and found and value in expected:
            return False
        if op == "$exists" and found != bool(expected):
            return False
        if op in _ORDER:
            try:
                if not (found and _ORDER[op](value, expected)):
                    return False
            except TypeError:
                return False
    return True


def _matches(document, query):
    for key, condition in (query or {}).items():
        if key == "$and":
            if not all(_matches(document, q) for q in condition):
                return False
        elif key == "$or":
            if not any(_matches(document, q) for q in condition):
                return False
        else:
            value, found = _get_field(document, key)
            if not _compare(value, found, condition):
                return False
    return True


def _apply_update(document, update):
    if not any(key.startswith("$") for key in update):       # Ersatz-Dokument
        replacement = {"_id": document.get("_id", ObjectId())}
        replacement.update({k: v for k, v in update.items() if k != "_id"})
        document.clear()
        document.update(replacement)
        return
    for op, fields in update.items():
        for key, value in fields.items():
            if op == "$set":
                document[key] = value
            elif op == "$unset":
                document.pop(key, None)
            elif op == "$inc":
                document[key] = document.get(key, 0) + value
            else:
                raise CommandError(9, "FailedToParse", f"Update-Operator {op} wird nicht unterstuetzt")


def _project(document, projection):
    if not projection:
        return document
    include = {k for k, v in projection.items() if v and k != "_id"}
    if include:
        result = {k: v for k, v in document.items() if k in include}
        if projection.get("_id", 1) and "_id" in document:
            result = {"_id": document["_id"], **result}
        return result
    return {k: v for k, v in document.items() if k not in projection}


# --- Befehle ---------------------------------------------------------------

def _hello(cmd, conn):
    reply = {
        "helloOk": True,
        "ismaster": True,
        "isWritablePrimary": True,
        "maxBsonObjectSize": 16 * 1024 * 1024,
        "maxMessageSizeBytes": 48000000,
        "maxWriteBatchSize": 100000,
        "localTime": datetime.datetime.now(datetime.timezone.utc),
        "logicalSessionTimeoutMinutes": 30,
        "connectionId": conn["id"],
        "minWireVersion": 0,
        "maxWireVersion": MAX_WIRE_VERSION,
        "readOnly": False,
    }
    if "saslSupportedMechs" in cmd:
        reply["saslSupportedMechs"] = ["SCRAM-SHA-256", "SCRAM-SHA-1"]
    if "speculativeAuthenticate" in cmd:
        try:
            reply["speculativeAuthenticate"] = _sasl_start(cmd["speculativeAuthenticate"], conn)
        except CommandError:
            pass                                       # Treiber macht dann den normalen Login
    return reply


def _scram_parts(message):
    return dict(part.split("=", 1) for part in message.split(",") if "=" in part)


def _sasl_start(cmd, conn):
    mechanism = cmd.get("mechanism")
    if mechanism == "SCRAM-SHA-256":
        digest, password = "sha256", MONGO_PASSWORD
    elif mechanism == "SCRAM-SHA-1":
        digest, password = "sha1", hashlib.md5(f"{MONGO_USER}:mongo:{MONGO_PASSWORD}".encode()).hexdigest()
    else:
        raise CommandError(2, "BadValue", f"Mechanismus {mechanism} wird nicht unterstuetzt")

    client_first = bytes(cmd["payload"]).decode("utf-8")
    client_first_bare = client_first.split(",", 2)[2]
    parts = _scram_parts(client_first_bare)
    nonce = parts["r"] + base64.b64encode(os.urandom(24)).decode()
    salt, iterations = os.urandom(16), 15000
    server_first = f"r={nonce},s={base64.b64encode(salt).decode()},i={iterations}"

    conn["sasl"] = {
        "user": parts["n"].replace("=2C", ",").replace("=3D", "="),
        "digest": digest,
        "salted": hashlib.pbkdf2_hmac(digest, password.encode("utf-8"), salt, iterations),
        "auth_start": f"{client_first_bare},{server_first}",
        "nonce": nonce,
    }
    return {"conversationId": 1, "done": False, "payload": server_first.encode()}


def _sasl_continue(cmd, conn):
    sasl = conn.get("sasl")
    if not sasl:
        raise CommandError(17, "ProtocolError", "saslContinue ohne saslStart")
    if sasl.get("done"):
        return {"conversationId": 1, "done": True, "payload": b""}

    client_final = bytes(cmd["payload"]).decode("utf-8")
    without_proof, proof = client_final.rsplit(",p=", 1)
    auth_message = f"{sasl['auth_start']},{without_proof}".encode()
    digest = sasl["digest"]

    client_key = hmac.new(sasl["salted"], b"Client Key", digest).digest()
    stored_key = hashlib.new(digest, client_key).digest()
    signature = hmac.new(stored_key, auth_message, digest).digest()
    sent_key = bytes(a ^ b for a, b in zip(base64.b64decode(proof), signature))

    if (sasl["user"] != MONGO_USER or _scram_parts(without_proof).get("r") != sasl["nonce"]
            or not hmac.compare_digest(hashlib.new(digest, sent_key).digest(), stored_key)):
        conn["sasl"] = None
        print(f"[mongo] Login fehlgeschlagen fuer '{sasl['user']}' ({conn['peer']})", flush=True)
        raise CommandError(18, "AuthenticationFailed", "Authentication failed.")

    server_key = hmac.new(sasl["salted"], b"Server Key", digest).digest()
    server_signature = hmac.new(server_key, auth_message, digest).digest()
    sasl["done"] = True
    conn["user"] = sasl["user"]
    host = conn["peer"].rsplit(":", 1)[0]
    if (sasl["user"], host) not in _logged_in:          # jede Gegenstelle nur beim ersten Mal melden
        _logged_in.add((sasl["user"], host))
        print(f"[mongo] {sasl['user']} von {host} eingeloggt", flush=True)
    return {"conversationId": 1, "done": True,
            "payload": b"v=" + base64.b64encode(server_signature)}


def _find(cmd, db):
    name = cmd["find"]
    with _data_lock:
        docs = [d for d in _collection(db, name) if _matches(d, cmd.get("filter"))]
    for key, direction in reversed(list((cmd.get("sort") or {}).items())):
        docs.sort(key=lambda d: (str(type(_get_field(d, key)[0])), _get_field(d, key)[0]),
                  reverse=direction < 0)
    docs = docs[cmd.get("skip", 0):]
    limit = abs(cmd.get("limit", 0) or 0)
    if limit:
        docs = docs[:limit]
    docs = [_project(d, cmd.get("projection")) for d in docs]
    return {"cursor": {"firstBatch": docs, "id": 0, "ns": f"{db}.{name}"}}


def _insert(cmd, db):
    documents = cmd.get("documents", [])
    with _data_lock:
        collection = _collection(db, cmd["insert"], create=True)
        for document in documents:
            if "_id" not in document:
                document = {"_id": ObjectId(), **document}
            collection.append(document)
        _save()
    return {"n": len(documents)}


def _update(cmd, db):
    matched = modified = 0
    upserted = []
    with _data_lock:
        collection = _collection(db, cmd["update"], create=True)
        for index, spec in enumerate(cmd.get("updates", [])):
            hits = [d for d in collection if _matches(d, spec.get("q"))]
            if not spec.get("multi"):
                hits = hits[:1]
            for document in hits:
                _apply_update(document, spec["u"])
            matched += len(hits)
            modified += len(hits)
            if not hits and spec.get("upsert"):
                document = {k: v for k, v in (spec.get("q") or {}).items() if not k.startswith("$")
                            and not isinstance(v, dict)}
                _apply_update(document, spec["u"])
                document.setdefault("_id", ObjectId())
                collection.append(document)
                upserted.append({"index": index, "_id": document["_id"]})
        _save()
    reply = {"n": matched + len(upserted), "nModified": modified}
    if upserted:
        reply["upserted"] = upserted
    return reply


def _delete(cmd, db):
    removed = 0
    with _data_lock:
        collection = _collection(db, cmd["delete"], create=True)
        for spec in cmd.get("deletes", []):
            hits = [d for d in collection if _matches(d, spec.get("q"))]
            if spec.get("limit"):
                hits = hits[:1]
            for document in hits:
                collection.remove(document)
            removed += len(hits)
        _save()
    return {"n": removed}


def _count(cmd, db):
    with _data_lock:
        return {"n": sum(1 for d in _collection(db, cmd["count"]) if _matches(d, cmd.get("query")))}


def _aggregate(cmd, db):
    """Nur die Stufen, die count_documents & Co. brauchen: $match, $skip, $limit, $count, $group mit $sum."""
    name = cmd["aggregate"]
    with _data_lock:
        docs = list(_collection(db, name))
    for stage in cmd.get("pipeline", []):
        (op, arg), = stage.items()
        if op == "$match":
            docs = [d for d in docs if _matches(d, arg)]
        elif op == "$skip":
            docs = docs[arg:]
        elif op == "$limit":
            docs = docs[:arg]
        elif op == "$count":
            docs = [{arg: len(docs)}] if docs else []
        elif op == "$project":
            docs = [_project(d, arg) for d in docs]
        elif op == "$group" and not isinstance(arg["_id"], str):
            group = {"_id": arg["_id"]}
            for field, spec in arg.items():
                if field != "_id":
                    (_, value), = spec.items()                # {"$sum": 1}
                    group[field] = value * len(docs) if isinstance(value, (int, float)) else len(docs)
            docs = [group] if docs else []
        else:
            raise CommandError(40324, "Location40324", f"Pipeline-Stufe {op} wird nicht unterstuetzt")
    return {"cursor": {"firstBatch": docs, "id": 0, "ns": f"{db}.{name}"}}


def _list_collections(cmd, db):
    with _data_lock:
        names = list(_data.get(db, {}))
    batch = [{"name": n, "type": "collection", "options": {}, "info": {"readOnly": False}} for n in names]
    return {"cursor": {"firstBatch": batch, "id": 0, "ns": f"{db}.$cmd.listCollections"}}


def _list_databases(cmd, db):
    with _data_lock:
        names = list(_data)
    return {"databases": [{"name": n, "sizeOnDisk": 0, "empty": False} for n in names], "totalSize": 0}


def _drop(cmd, db):
    with _data_lock:
        _data.get(db, {}).pop(cmd["drop"], None)
        _save()
    return {}


def _create(cmd, db):
    with _data_lock:
        _collection(db, cmd["create"], create=True)
        _save()
    return {}


def _build_info(cmd, db):
    return {"version": "6.0.0", "versionArray": [6, 0, 0, 0], "gitVersion": "the-ship", "bits": 64,
            "maxBsonObjectSize": 16 * 1024 * 1024, "modules": []}


OPEN_COMMANDS = {                                    # geht auch ohne Login
    "hello": lambda cmd, db, conn: _hello(cmd, conn),
    "ismaster": lambda cmd, db, conn: _hello(cmd, conn),
    "isMaster": lambda cmd, db, conn: _hello(cmd, conn),
    "saslStart": lambda cmd, db, conn: _sasl_start(cmd, conn),
    "saslContinue": lambda cmd, db, conn: _sasl_continue(cmd, conn),
    "ping": lambda cmd, db, conn: {},
    "buildInfo": lambda cmd, db, conn: _build_info(cmd, db),
    "buildinfo": lambda cmd, db, conn: _build_info(cmd, db),
    "endSessions": lambda cmd, db, conn: {},
    "logout": lambda cmd, db, conn: conn.update(user=None) or {},
}

COMMANDS = {                                         # nur mit Login
    "find": _find,
    "insert": _insert,
    "update": _update,
    "delete": _delete,
    "count": _count,
    "aggregate": _aggregate,
    "listCollections": _list_collections,
    "listDatabases": _list_databases,
    "drop": _drop,
    "create": _create,
    "killCursors": lambda cmd, db: {"cursorsKilled": cmd.get("cursors", [])},
    "getMore": lambda cmd, db: {"cursor": {"nextBatch": [], "id": 0, "ns": f"{db}.{cmd.get('collection')}"}},
}


def _run_command(cmd, conn):
    name = next(iter(cmd))
    db = cmd.get("$db", "admin")
    try:
        if name in OPEN_COMMANDS:
            reply = OPEN_COMMANDS[name](cmd, db, conn)
        elif name in COMMANDS:
            if not conn.get("user"):
                raise CommandError(13, "Unauthorized", f"command {name} requires authentication")
            if db not in (MONGO_DB, "admin"):
                raise CommandError(13, "Unauthorized", f"not authorized on {db} to execute command {name}")
            reply = COMMANDS[name](cmd, db)
        else:
            raise CommandError(59, "CommandNotFound", f"no such command: '{name}'")
        reply["ok"] = 1.0
        return reply
    except CommandError as exc:
        return {"ok": 0.0, "errmsg": str(exc), "code": exc.code, "codeName": exc.name}
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        return {"ok": 0.0, "errmsg": f"{name}: {exc!r}", "code": 9, "codeName": "FailedToParse"}


# --- Wire-Protokoll ---------------------------------------------------------

def _read_exact(sock, count):
    data = b""
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise ConnectionError("Client hat die Verbindung geschlossen")
        data += chunk
    return data


def _reply(sock, request_id, op_code, body):
    header = struct.pack("<iiii", 16 + len(body), next(_connection_ids), request_id, op_code)
    sock.sendall(header + body)


def _handle_op_msg(sock, request_id, body, conn):
    flags = struct.unpack_from("<I", body, 0)[0]
    end = len(body) - (4 if flags & 1 else 0)          # Bit 0: Pruefsumme am Ende
    pos, cmd, sequences = 4, None, {}
    while pos < end:
        kind = body[pos]
        pos += 1
        if kind == 0:
            cmd, pos = decode(body, pos)
        else:                                          # Kind 1: Dokument-Folge (z.B. insert.documents)
            size = struct.unpack_from("<i", body, pos)[0]
            section_end = pos + size
            identifier_end = body.index(b"\x00", pos + 4)
            identifier = body[pos + 4:identifier_end].decode()
            pos, docs = identifier_end + 1, []
            while pos < section_end:
                doc, pos = decode(body, pos)
                docs.append(doc)
            sequences[identifier] = docs
    cmd.update(sequences)
    reply = _run_command(cmd, conn)
    if not flags & 2:                                  # Bit 1 (moreToCome): keine Antwort erwartet
        _reply(sock, request_id, OP_MSG, struct.pack("<I", 0) + b"\x00" + encode(reply))


def _handle_op_query(sock, request_id, body, conn):
    end = body.index(b"\x00", 4)
    namespace = body[4:end].decode()
    query, _ = decode(body, end + 9)
    if "$query" in query:
        query = query["$query"]
    query["$db"] = namespace.split(".", 1)[0]
    reply = _run_command(query, conn)
    _reply(sock, request_id, OP_REPLY, struct.pack("<iqii", 0, 0, 0, 1) + encode(reply))


def _handle_client(sock, address):
    conn = {"id": next(_connection_ids), "peer": f"{address[0]}:{address[1]}", "user": None}
    try:
        while True:
            length, request_id, _, op_code = struct.unpack("<iiii", _read_exact(sock, 16))
            body = _read_exact(sock, length - 16)
            if op_code == OP_MSG:
                _handle_op_msg(sock, request_id, body, conn)
            elif op_code == OP_QUERY:
                _handle_op_query(sock, request_id, body, conn)
            else:
                print(f"[mongo] unbekannter opCode {op_code} von {conn['peer']}", flush=True)
                break
    except (OSError, ConnectionError):
        pass
    except Exception as exc:
        print(f"[mongo] Fehler mit {conn['peer']}: {exc!r}", flush=True)
    finally:
        sock.close()


def _serve_forever():
    _load()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", MONGO_PORT))
    server.listen()
    print(f"[mongo] MongoDB-Server laeuft auf Port {MONGO_PORT} (DB {MONGO_DB}, User {MONGO_USER})", flush=True)
    while True:
        sock, address = server.accept()
        threading.Thread(target=_handle_client, args=(sock, address), daemon=True).start()


# --- Starten aus mission_6 -------------------------------------------------

def _is_running():
    try:
        socket.create_connection(("127.0.0.1", MONGO_PORT), timeout=1).close()
        return True
    except OSError:
        return False


def _follow_log(start):
    """Zeigt neue Zeilen aus mongo_server.log in der Ausgabe von main.py an."""
    with open(LOG_FILE, encoding="utf-8", errors="replace") as log:
        log.seek(start)
        while True:
            line = log.readline()
            if line:
                print(line, end="", flush=True)
            else:
                time.sleep(0.3)


def start_mongo_server():
    """Startet den MongoDB-Server als eigenen Hintergrund-Prozess, falls auf dem Port noch keiner laeuft.
    Laeuft dort schon einer (unser alter Prozess oder ein echtes mongod), wird dieser benutzt."""
    LOG_FILE.touch()
    start = LOG_FILE.stat().st_size
    if _is_running():
        print(f"[mongo] MongoDB laeuft schon auf Port {MONGO_PORT} - benutze sie.", flush=True)
    else:
        with open(LOG_FILE, "a") as log:
            subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve())],
                             cwd=str(Path(__file__).parent), stdout=log, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        for _ in range(50):
            if _is_running():
                break
            time.sleep(0.1)
        else:
            raise RuntimeError(f"MongoDB-Server startet nicht - siehe {LOG_FILE}")
    threading.Thread(target=_follow_log, args=(start,), daemon=True).start()


if __name__ == "__main__":
    _serve_forever()
