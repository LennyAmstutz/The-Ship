import base64
import hashlib
import hmac
import itertools
import os
import socket
import struct
import threading

from Actions.bson_codec import decode, encode

# Kleiner MongoDB-Client (OP_MSG + Login mit SCRAM-SHA-256) - ohne pymongo, das auf dem Schiff fehlt.
# Funktioniert mit unserem mongo_server.py und mit einem echten mongod.

OP_MSG = 2013


class MongoError(Exception):
    pass


class MongoClient:
    def __init__(self, host, port, user, password, db, timeout=5):
        self.host, self.port = host, port
        self.user, self.password, self.db = user, password, db
        self.timeout = timeout
        self._sock = None
        self._lock = threading.Lock()
        self._ids = itertools.count(1)

    # --- Verbindung -------------------------------------------------------

    def _connect(self):
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._send({"hello": 1, "client": {"application": {"name": "lenny-mission6"}}, "$db": "admin"})
        self._login()

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None

    def _read_exact(self, count):
        data = b""
        while len(data) < count:
            chunk = self._sock.recv(count - len(data))
            if not chunk:
                raise ConnectionError("MongoDB hat die Verbindung geschlossen")
            data += chunk
        return data

    def _send(self, command):
        body = struct.pack("<I", 0) + b"\x00" + encode(command)
        self._sock.sendall(struct.pack("<iiii", 16 + len(body), next(self._ids), 0, OP_MSG) + body)
        length, _, _, op_code = struct.unpack("<iiii", self._read_exact(16))
        reply = self._read_exact(length - 16)
        if op_code != OP_MSG:
            raise MongoError(f"unerwartete Antwort (opCode {op_code})")
        result, _ = decode(reply, 5)                   # 4 Bytes Flags + 1 Byte Sektion 0
        if not result.get("ok"):
            raise MongoError(f"{next(iter(command))}: {result.get('errmsg')} ({result.get('codeName')})")
        return result

    def _login(self):
        """SCRAM-SHA-256 (RFC 5802/7677), so wie mongosh und pymongo es machen."""
        client_nonce = base64.b64encode(os.urandom(24)).decode()
        user = self.user.replace("=", "=3D").replace(",", "=2C")
        client_first_bare = f"n={user},r={client_nonce}"

        start = self._send({"saslStart": 1, "mechanism": "SCRAM-SHA-256",
                            "payload": f"n,,{client_first_bare}".encode(),
                            "options": {"skipEmptyExchange": True}, "$db": self.db})
        server_first = bytes(start["payload"]).decode()
        parts = dict(part.split("=", 1) for part in server_first.split(","))
        if not parts["r"].startswith(client_nonce):
            raise MongoError("Server-Nonce passt nicht")

        salted = hashlib.pbkdf2_hmac("sha256", self.password.encode(), base64.b64decode(parts["s"]), int(parts["i"]))
        client_key = hmac.new(salted, b"Client Key", "sha256").digest()
        stored_key = hashlib.sha256(client_key).digest()
        without_proof = f"c=biws,r={parts['r']}"
        auth_message = f"{client_first_bare},{server_first},{without_proof}".encode()
        signature = hmac.new(stored_key, auth_message, "sha256").digest()
        proof = base64.b64encode(bytes(a ^ b for a, b in zip(client_key, signature))).decode()

        final = self._send({"saslContinue": 1, "conversationId": start["conversationId"],
                            "payload": f"{without_proof},p={proof}".encode(), "$db": self.db})
        server_key = hmac.new(salted, b"Server Key", "sha256").digest()
        expected = b"v=" + base64.b64encode(hmac.new(server_key, auth_message, "sha256").digest())
        if bytes(final["payload"]) != expected:
            raise MongoError("Server-Signatur ist falsch")
        while not final.get("done"):
            final = self._send({"saslContinue": 1, "conversationId": start["conversationId"],
                                "payload": b"", "$db": self.db})

    def command(self, command):
        """Fuehrt einen Befehl auf self.db aus. Bei Verbindungsfehlern wird einmal neu verbunden."""
        command = {**command, "$db": self.db}
        with self._lock:
            for attempt in (1, 2):
                try:
                    if self._sock is None:
                        self._connect()
                    return self._send(command)
                except (OSError, ConnectionError):
                    self.close()
                    if attempt == 2:
                        raise

    # --- CRUD ------------------------------------------------------------

    def find(self, collection, query=None):
        return self.command({"find": collection, "filter": query or {}})["cursor"]["firstBatch"]

    def insert_one(self, collection, document):
        return self.command({"insert": collection, "documents": [document]})

    def delete_many(self, collection, query=None):
        return self.command({"delete": collection, "deletes": [{"q": query or {}, "limit": 0}]})["n"]

    def replace_one(self, collection, query, document, upsert=False):
        return self.command({"update": collection,
                             "updates": [{"q": query, "u": document, "upsert": upsert, "multi": False}]})
