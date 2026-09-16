import json

import websocket

from config import COMM_MODULE_ELYSE_WS_URL, ELYSE_STATION

_ws = None


def connect():
    global _ws
    _ws = websocket.create_connection(COMM_MODULE_ELYSE_WS_URL)
    return _ws


def receive_message():
    if _ws is None:
        connect()
    raw = _ws.recv()
    return json.loads(raw)


def send_message(msg, destination=ELYSE_STATION):
    if _ws is None:
        connect()
    payload = {"destination": destination, "msg": msg}
    _ws.send(json.dumps(payload))


def close():
    global _ws
    if _ws is not None:
        _ws.close()
        _ws = None