import json

import websocket

from config import command, ELYSE_STATION

_ws_recv = None
_ws_send = None


def _connect_recv():
    global _ws_recv
    _ws_recv = websocket.create_connection(command["comm_elyse_ws"])
    return _ws_recv


def _connect_send():
    global _ws_send
    _ws_send = websocket.create_connection(command["comm_elyse_ws"])
    return _ws_send


def connect():
    """Baut beide Verbindungen auf (getrennt fuer Senden/Empfangen)."""
    _connect_recv()
    _connect_send()


def receive_message():
    global _ws_recv
    if _ws_recv is None or not _ws_recv.connected:
        _connect_recv()
    try:
        raw = _ws_recv.recv()
    except Exception:
        _connect_recv()
        raw = _ws_recv.recv()
    return json.loads(raw)


def send_message(msg, destination=ELYSE_STATION):
    global _ws_send
    if _ws_send is None or not _ws_send.connected:
        _connect_send()
    payload = {"destination": destination, "msg": msg}
    try:
        _ws_send.send(json.dumps(payload))
    except Exception:
        _connect_send()
        _ws_send.send(json.dumps(payload))


def close():
    global _ws_recv, _ws_send
    for ws in (_ws_recv, _ws_send):
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
    _ws_recv = None
    _ws_send = None