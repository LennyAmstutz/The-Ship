import socket
import struct
import threading
import time

from config import AURORA_HOST, AURORA_PORT

# Protokoll vom Comm Module Aurora (TCP, 192.168.101.51:2031), jede Nachricht:
#   2 Bytes  Laenge von msg (uint16, big endian)
#   1 Byte   Laenge vom Namen (uint8)
#   n Bytes  Name (UTF-8) - von Aurora: dst (Ziel), an Aurora: src (Absender)
#   m Bytes  msg
# Beispiel: 00 04 | 03 | "src" | "test"  ->  src="src", msg="test"

_sock = None
_lock = threading.Lock()


def encode(name, msg):
    raw_name = name.encode("utf-8")
    return struct.pack("!HB", len(msg), len(raw_name)) + raw_name + msg


def _read_exact(sock, count):
    data = b""
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise ConnectionError("Aurora hat die Verbindung geschlossen")
        data += chunk
    return data


def read_message(sock):
    """Liest eine Nachricht und gibt (name, msg_bytes) zurueck."""
    msg_size, name_size = struct.unpack("!HB", _read_exact(sock, 3))
    name = _read_exact(sock, name_size).decode("utf-8")
    return name, _read_exact(sock, msg_size)


def _connect():
    global _sock
    with _lock:
        while _sock is None:
            try:
                _sock = socket.create_connection((AURORA_HOST, AURORA_PORT), timeout=10)
                _sock.settimeout(None)
                print(f"[aurora] verbunden mit {AURORA_HOST}:{AURORA_PORT}", flush=True)
            except OSError as exc:
                print(f"[aurora] {AURORA_HOST}:{AURORA_PORT} nicht erreichbar ({exc}), naechster Versuch", flush=True)
                time.sleep(2)
        return _sock


def _drop(broken):
    global _sock
    with _lock:
        if _sock is broken:
            try:
                broken.close()
            except OSError:
                pass
            _sock = None


def _read_loop(on_message):
    while True:
        current = _connect()
        try:
            dst, msg = read_message(current)
        except (OSError, UnicodeDecodeError, struct.error) as exc:
            print("[aurora] Verbindung weg beim Lesen:", exc, flush=True)
            _drop(current)
            continue
        try:
            on_message(dst, msg)
        except Exception as exc:
            print("[aurora] Fehler in on_message:", exc, flush=True)


def connect(on_message):
    """Verbindet mit Aurora und ruft on_message(dst, msg_bytes) fuer jede Nachricht auf,
    die Aurora versenden will. Bei Abbruch wird selbst neu verbunden."""
    _connect()
    threading.Thread(target=_read_loop, args=(on_message,), daemon=True).start()


def send_message(src, msg):
    """Stellt msg (bytes) an Aurora zu, mit src als Absender-Station."""
    current = _connect()
    try:
        current.sendall(encode(src, msg))
    except OSError as exc:
        print("[aurora] Verbindung weg beim Senden:", exc, flush=True)
        _drop(current)
        raise
