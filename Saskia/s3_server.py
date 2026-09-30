import datetime
import hashlib
import hmac
import re
import socket
import subprocess
import sys
import threading
import time
from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit
from xml.sax.saxutils import escape

from Actions import s3_sigv4
from config import S3_ACCESS_KEY, S3_BUCKET, S3_CHECK_SIGNATURE, S3_PORT, S3_REGION, S3_SECRET_KEY

# Kleiner S3-Server fuer Mission 9 - ersetzt MinIO, wenn keins installiert ist.
# Der Analyzer Gamma liest mit access key theship / secret key theship1234 regelmaessig
#   http://192.168.101.51:2016/analyzer-gamma/data.hex
# (vorher fragt der minio-Client nach der Region: GET /analyzer-gamma?location=).
#
# Unterstuetzt: ListBuckets, Create/Head/Delete Bucket, GetBucketLocation, ListObjects (v1 + v2),
# Put/Get/Head/Delete Object. Jede Anfrage muss mit AWS Signature V4 unterschrieben sein.
# Jede Verbindung laeuft in einem eigenen Thread (ThreadingHTTPServer) - der Analyzer kann also lesen,
# waehrend mission_9 gerade eine neue Messung hochlaedt. Hochladen ist atomar (tmp-Datei + rename),
# der Analyzer sieht darum nie eine halb geschriebene data.hex.
#
# Die Dateien liegen in s3_data/<bucket>/<key> und ueberleben so einen Neustart.
# Laeuft wie der MongoDB-Server als EIGENER Prozess weiter, auch wenn main.py beendet wird.
# Log: s3_server.log (mission_9 zeigt es mit an). Stoppen: pkill -f s3_server.py

DATA_DIR = Path(__file__).with_name("s3_data")
LOG_FILE = Path(__file__).with_name("s3_server.log")
XMLNS = "http://s3.amazonaws.com/doc/2006-03-01/"
BUCKET_NAME = re.compile(r"^[a-z0-9][a-z0-9.\-]{1,61}[a-z0-9]$")

_write_lock = threading.Lock()
_get_counts = {}                     # "bucket/key" -> wie oft gelesen (fuers Log)


class S3Error(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code = status, code


def log(text):
    print(f"[s3] {datetime.datetime.now():%H:%M:%S} {text}", flush=True)


# --- Speicher --------------------------------------------------------------

def _bucket_dir(bucket):
    return DATA_DIR / bucket


def _object_path(bucket, key):
    path = (_bucket_dir(bucket) / key).resolve()
    if _bucket_dir(bucket).resolve() not in path.parents:
        raise S3Error(400, "InvalidArgument", "ungueltiger Key")
    return path


def _require_bucket(bucket):
    if not _bucket_dir(bucket).is_dir():
        raise S3Error(404, "NoSuchBucket", f"Bucket {bucket} gibt es nicht")


def _objects(bucket):
    base = _bucket_dir(bucket)
    for path in sorted(p for p in base.rglob("*") if p.is_file() and not p.name.endswith(".s3tmp")):
        yield path.relative_to(base).as_posix(), path


def _etag(data):
    return f'"{hashlib.md5(data).hexdigest()}"'


def _iso(timestamp):
    return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _decode_aws_chunked(body):
    """Streaming-Uploads (aws cli, mc): <hex-laenge>[;chunk-signature=..]\\r\\n<daten>\\r\\n ... 0\\r\\n"""
    out, pos = b"", 0
    while True:
        line_end = body.index(b"\r\n", pos)
        size = int(body[pos:line_end].split(b";")[0], 16)
        pos = line_end + 2
        if size == 0:
            return out
        out += body[pos:pos + size]
        pos += size + 2


# --- HTTP ------------------------------------------------------------------

class S3Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"            # Keep-Alive: der Analyzer liest immer wieder
    server_version = "TheShipS3/1.0"

    def log_message(self, fmt, *args):       # Standard-Log pro Anfrage ist zu viel - wir loggen selbst
        pass

    # --- Antworten --------------------------------------------------------

    def _send(self, status, body=b"", content_type="application/xml", headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("x-amz-request-id", f"{time.time_ns():X}")
        self.send_header("Date", formatdate(usegmt=True))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_xml(self, xml, status=200):
        self._send(status, ('<?xml version="1.0" encoding="UTF-8"?>\n' + xml).encode())

    def _send_error(self, error):
        xml = (f"<Error><Code>{error.code}</Code><Message>{escape(str(error))}</Message>"
               f"<Resource>{escape(self.path)}</Resource><RequestId>{time.time_ns():X}</RequestId></Error>")
        self._send_xml(xml, error.status)

    # --- Anfrage lesen ----------------------------------------------------

    def _read_body(self):
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            body = b""
            while True:
                size = int(self.rfile.readline().split(b";")[0], 16)
                if size == 0:
                    while self.rfile.readline() not in (b"\r\n", b"\n", b""):
                        pass
                    return body
                body += self.rfile.read(size)
                self.rfile.readline()
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    def _check_auth(self, raw_path, query_pairs, body):
        """Prueft die AWS-Signatur V4 (Header-Variante oder vorsignierte URL)."""
        headers = {name.lower(): value for name, value in self.headers.items()}
        query = dict(query_pairs)
        if "X-Amz-Signature" in query:                              # vorsignierte URL
            credential = query["X-Amz-Credential"]
            auth = {"access_key": credential.split("/")[0], "scope": credential.partition("/")[2],
                    "signed_headers": query["X-Amz-SignedHeaders"].split(";"),
                    "signature": query["X-Amz-Signature"]}
            amz_date = query["X-Amz-Date"]
            payload_hash = s3_sigv4.UNSIGNED_PAYLOAD
            query_pairs = [(k, v) for k, v in query_pairs if k != "X-Amz-Signature"]
        else:
            try:
                auth = s3_sigv4.parse_authorization(headers.get("authorization"))
            except (ValueError, KeyError):
                raise S3Error(403, "AccessDenied", "Anfrage ist nicht mit AWS Signature V4 unterschrieben")
            amz_date = headers.get("x-amz-date", "")
            payload_hash = headers.get("x-amz-content-sha256", s3_sigv4.UNSIGNED_PAYLOAD)

        if auth["access_key"] != S3_ACCESS_KEY:
            raise S3Error(403, "InvalidAccessKeyId", f"access key {auth['access_key']!r} ist unbekannt")
        if not S3_CHECK_SIGNATURE:
            return
        expected = s3_sigv4.signature(S3_SECRET_KEY, self.command, raw_path, query_pairs, headers,
                                      auth["signed_headers"], payload_hash, amz_date, auth["scope"])
        if not hmac.compare_digest(expected, auth["signature"]):
            raise S3Error(403, "SignatureDoesNotMatch", "Signatur stimmt nicht (falscher secret key?)")
        if (not payload_hash.startswith(("UNSIGNED", "STREAMING"))
                and payload_hash != s3_sigv4.sha256_hex(body)):
            raise S3Error(400, "XAmzContentSHA256Mismatch", "Body passt nicht zu x-amz-content-sha256")

    # --- Verteiler --------------------------------------------------------

    def _handle(self):
        url = urlsplit(self.path)
        raw_path = url.path or "/"
        query_pairs = parse_qsl(url.query, keep_blank_values=True)
        query = dict(query_pairs)
        parts = unquote(raw_path).lstrip("/").split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        body = self._read_body() if self.command in ("PUT", "POST") else b""

        try:
            self._check_auth(raw_path, query_pairs, body)
            if "aws-chunked" in self.headers.get("Content-Encoding", "") or \
                    self.headers.get("x-amz-content-sha256", "").startswith("STREAMING"):
                body = _decode_aws_chunked(body)

            if not bucket:
                if self.command == "GET":
                    return self._list_buckets()
            elif not key:
                if self.command == "GET" and "location" in query:
                    return self._bucket_location(bucket)
                if self.command == "GET":
                    return self._list_objects(bucket, query)
                if self.command == "HEAD":
                    _require_bucket(bucket)
                    return self._send(200, headers={"x-amz-bucket-region": S3_REGION})
                if self.command == "PUT":
                    return self._create_bucket(bucket)
                if self.command == "DELETE":
                    return self._delete_bucket(bucket)
            else:
                if self.command in ("GET", "HEAD"):
                    return self._get_object(bucket, key)
                if self.command == "PUT":
                    return self._put_object(bucket, key, body)
                if self.command == "DELETE":
                    return self._delete_object(bucket, key)
            raise S3Error(501, "NotImplemented", f"{self.command} {self.path} kann dieser Server nicht")
        except S3Error as error:
            log(f"{self.client_address[0]} {self.command} {self.path} -> {error.status} {error.code}: {error}")
            self._send_error(error)

    do_GET = do_HEAD = do_PUT = do_POST = do_DELETE = _handle

    # --- Buckets ----------------------------------------------------------

    def _list_buckets(self):
        DATA_DIR.mkdir(exist_ok=True)
        buckets = "".join(f"<Bucket><Name>{escape(p.name)}</Name><CreationDate>{_iso(p.stat().st_mtime)}"
                          f"</CreationDate></Bucket>" for p in sorted(DATA_DIR.iterdir()) if p.is_dir())
        self._send_xml(f'<ListAllMyBucketsResult xmlns="{XMLNS}"><Owner><ID>{S3_ACCESS_KEY}</ID>'
                       f"<DisplayName>{S3_ACCESS_KEY}</DisplayName></Owner><Buckets>{buckets}</Buckets>"
                       f"</ListAllMyBucketsResult>")

    def _bucket_location(self, bucket):
        _require_bucket(bucket)
        # leer = us-east-1 (so antwortet auch AWS)
        location = "" if S3_REGION == "us-east-1" else S3_REGION
        self._send_xml(f'<LocationConstraint xmlns="{XMLNS}">{location}</LocationConstraint>')

    def _create_bucket(self, bucket):
        if not BUCKET_NAME.match(bucket):
            raise S3Error(400, "InvalidBucketName", f"{bucket!r} ist kein gueltiger Bucket-Name")
        if _bucket_dir(bucket).is_dir():
            raise S3Error(409, "BucketAlreadyOwnedByYou", f"Bucket {bucket} gibt es schon")
        _bucket_dir(bucket).mkdir(parents=True)
        log(f"Bucket {bucket} angelegt")
        self._send(200, headers={"Location": f"/{bucket}"})

    def _delete_bucket(self, bucket):
        _require_bucket(bucket)
        if any(True for _ in _objects(bucket)):
            raise S3Error(409, "BucketNotEmpty", f"Bucket {bucket} ist nicht leer")
        _bucket_dir(bucket).rmdir()
        log(f"Bucket {bucket} geloescht")
        self._send(204)

    def _list_objects(self, bucket, query):
        _require_bucket(bucket)
        prefix = query.get("prefix", "")
        v2 = query.get("list-type") == "2"
        start_after = query.get("start-after" if v2 else "marker", "")
        start_after = query.get("continuation-token", start_after) if v2 else start_after
        max_keys = int(query.get("max-keys", 1000))

        matches = [(key, path) for key, path in _objects(bucket) if key.startswith(prefix) and key > start_after]
        page, truncated = matches[:max_keys], len(matches) > max_keys
        contents = "".join(
            f"<Contents><Key>{escape(key)}</Key><LastModified>{_iso(path.stat().st_mtime)}</LastModified>"
            f"<ETag>{escape(_etag(path.read_bytes()))}</ETag><Size>{path.stat().st_size}</Size>"
            f"<StorageClass>STANDARD</StorageClass></Contents>" for key, path in page)
        extra = f"<KeyCount>{len(page)}</KeyCount>" if v2 else f"<Marker>{escape(start_after)}</Marker>"
        if truncated:
            extra += (f"<NextContinuationToken>{escape(page[-1][0])}</NextContinuationToken>" if v2
                      else f"<NextMarker>{escape(page[-1][0])}</NextMarker>")
        self._send_xml(f'<ListBucketResult xmlns="{XMLNS}"><Name>{escape(bucket)}</Name>'
                       f"<Prefix>{escape(prefix)}</Prefix>{extra}<MaxKeys>{max_keys}</MaxKeys>"
                       f"<IsTruncated>{str(truncated).lower()}</IsTruncated>{contents}</ListBucketResult>")

    # --- Objekte ----------------------------------------------------------

    def _get_object(self, bucket, key):
        _require_bucket(bucket)
        path = _object_path(bucket, key)
        if not path.is_file():
            raise S3Error(404, "NoSuchKey", f"{bucket}/{key} gibt es nicht")
        data = path.read_bytes()
        name = f"{bucket}/{key}"
        _get_counts[name] = _get_counts.get(name, 0) + 1
        count = _get_counts[name]
        if self.command == "GET" and (count == 1 or count % 20 == 0):
            log(f"{self.client_address[0]} liest {name} ({count}. Mal): {data[:40].decode(errors='replace')}...")
        self._send(200, data, content_type="application/octet-stream", headers={
            "ETag": _etag(data),
            "Last-Modified": formatdate(path.stat().st_mtime, usegmt=True),
            "Accept-Ranges": "bytes",
        })

    def _put_object(self, bucket, key, data):
        _require_bucket(bucket)
        path = _object_path(bucket, key)
        with _write_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".s3tmp")
            tmp.write_bytes(data)
            tmp.replace(path)                 # atomar: Leser sehen die alte ODER die neue Datei
        self._send(200, headers={"ETag": _etag(data)})

    def _delete_object(self, bucket, key):
        _require_bucket(bucket)
        _object_path(bucket, key).unlink(missing_ok=True)
        self._send(204)


def _serve_forever():
    _bucket_dir(S3_BUCKET).mkdir(parents=True, exist_ok=True)        # den Bucket braucht der Analyzer
    server = ThreadingHTTPServer(("0.0.0.0", S3_PORT), S3Handler)
    server.daemon_threads = True
    log(f"S3-Server laeuft auf Port {S3_PORT} (Bucket {S3_BUCKET}, access key {S3_ACCESS_KEY}, "
        f"Daten in {DATA_DIR})")
    server.serve_forever()


# --- Starten aus mission_9 -------------------------------------------------

def _is_running():
    try:
        socket.create_connection(("127.0.0.1", S3_PORT), timeout=1).close()
        return True
    except OSError:
        return False


def _follow_log(start):
    """Zeigt neue Zeilen aus s3_server.log in der Ausgabe von main.py an."""
    with open(LOG_FILE, encoding="utf-8", errors="replace") as log_file:
        log_file.seek(start)
        while True:
            line = log_file.readline()
            if line:
                print(line, end="", flush=True)
            else:
                time.sleep(0.3)


def start_s3_server():
    """Startet den S3-Server als eigenen Hintergrund-Prozess, falls auf dem Port noch keiner laeuft.
    Laeuft dort schon einer (unser alter Prozess oder ein echtes MinIO), wird dieser benutzt."""
    LOG_FILE.touch()
    start = LOG_FILE.stat().st_size
    if _is_running():
        print(f"[s3] Auf Port {S3_PORT} laeuft schon ein S3-Server - benutze ihn.", flush=True)
    else:
        with open(LOG_FILE, "a") as log_file:
            subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve())],
                             cwd=str(Path(__file__).parent), stdout=log_file, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        for _ in range(50):
            if _is_running():
                break
            time.sleep(0.1)
        else:
            raise RuntimeError(f"S3-Server startet nicht - siehe {LOG_FILE}")
    threading.Thread(target=_follow_log, args=(start,), daemon=True).start()


if __name__ == "__main__":
    _serve_forever()
