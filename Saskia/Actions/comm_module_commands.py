import json
import threading
import time

import websocket

from config import command, COMM_KEY

# Eine einzige Verbindung fuers Senden UND Empfangen. Das Comm-Modul ist nur offen,
# solange die Station in Reichweite ist - darum wird bei jedem Fehler neu verbunden.
_lock = threading.Lock()
_ws = None
_connected_since = 0.0
_sent_count = 0


def _connect():
    global _ws, _connected_since, _sent_count
    with _lock:
        while _ws is None:
            try:
                _ws = websocket.create_connection(command["comm_shangris_ws"])
                _connected_since = time.monotonic()
                _sent_count = 0
                print("[comm] Comm-Modul verbunden", flush=True)
            except OSError:
                print("[comm] Comm-Modul noch zu, naechster Versuch", flush=True)
                time.sleep(2)
        return _ws


def _drop(broken):
    global _ws
    with _lock:
        if _ws is broken:
            print(f"[comm]  (hielt {time.monotonic() - _connected_since:.1f}s, "
                  f"{_sent_count} Nachrichten gesendet)", flush=True)
            try:
                broken.close()
            except Exception:
                pass
            _ws = None


def connect():
    _connect()


def payload(message):
    """Inhalt einer Nachricht - je nach Station unter "msg" oder "data"."""
    return message.get("msg", message.get("data"))


def receive_message():
    """Wartet auf die naechste Nachricht vom eigenen Comm-Modul."""
    while True:
        current = _connect()
        try:
            raw = current.recv()
        except Exception as exc:
            print("[comm] Station weg beim Lesen:", type(exc).__name__, flush=True)
            _drop(current)
            continue

        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if raw.strip():
            return json.loads(raw)


def send_message(msg, source):
    """Stellt eine Nachricht ans eigene Comm-Modul zu, mit der Station, von der sie kommt."""
    global _sent_count
    current = _connect()
    try:
        current.send(json.dumps({"source": source, COMM_KEY: msg}))
        _sent_count += 1
    except Exception as exc:
        print("[comm] Station weg beim Senden:", type(exc).__name__, flush=True)
        _drop(current)
        raise


def close():
    global _ws
    with _lock:
        if _ws is not None:
            try:
                _ws.close()
            except Exception:
                pass
        _ws = None
