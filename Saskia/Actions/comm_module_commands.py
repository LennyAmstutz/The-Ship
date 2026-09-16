import json

import websocket

from config import command, SHANGRIS_STATION

_ws = None


def connect():
    global _ws
    _ws = websocket.create_connection(command["comm_shangris_ws"])
    return _ws


def _ensure_connected():
    global _ws
    if _ws is None or not _ws.connected:
        connect()


def receive_message():
    _ensure_connected()
    try:
        raw = _ws.recv()
    except Exception:
        connect()
        raw = _ws.recv()
    return json.loads(raw)


def send_message(msg, destination=SHANGRIS_STATION):
    _ensure_connected()
    payload = {"destination": destination, "data": msg}
    try:
        _ws.send(json.dumps(payload))
    except Exception:
        connect()
        _ws.send(json.dumps(payload))


def close():
    global _ws
    if _ws is not None:
        try:
            _ws.close()
        except Exception:
            pass
        _ws = None