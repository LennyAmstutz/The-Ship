from pathlib import Path
import base64
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from Actions.aurora_commands import connect, send_message
from Actions.communication_commands import stations_in_reach
from Actions.steering_commands import set_target, wait_until_in_reach
from relay_server import start_relay_server, inbox
from config import (
    command,
    VESTA_STATION,
    AURORA_STATION,
    AURORA_TARGET,
    SEND_PAUSE,
    RANGE_CHECK_SECONDS,
)


def forward_to_partner(message):
    response = requests.post(command["partner_relay"], json=message, timeout=5)
    response.raise_for_status()


def fly_to_aurora():
    set_target(AURORA_TARGET)
    print("[mission5] unterwegs zu", AURORA_STATION)
    wait_until_in_reach(AURORA_STATION, timeout=None)
    print("[mission5] In Reichweite von", AURORA_STATION)


def stay_in_range():
    while True:
        try:
            if AURORA_STATION not in stations_in_reach()["stations"]:
                print("[mission5] abgedriftet, Kurs neu setzen", flush=True)
                set_target(AURORA_TARGET)
        except Exception as exc:
            print("[mission5] Fehler beim Reichweite-Check:", exc)
        time.sleep(RANGE_CHECK_SECONDS)


def aurora_to_partner(dst, msg):
    """Aurora schickt (dst, msg-Bytes) - geht an Lenny (Vesta) weiter.
    Zwischen den Schiffen wird msg base64-codiert, damit die Bytes in JSON passen."""
    forward = {"source": AURORA_STATION, "data": base64.b64encode(msg).decode("ascii")}
    try:
        forward_to_partner(forward)
        print(f"[mission5] Aurora -> {dst} weitergeleitet ({len(msg)} Bytes)")
    except Exception as exc:
        print("[mission5] Fehler beim Weiterleiten an Partner:", exc)


def partner_to_aurora():
    """Nachrichten vom Partner an Aurora. Staut sich etwas an, nur die neueste."""
    while True:
        incoming = inbox.get()
        while not inbox.empty():
            incoming = inbox.get()

        source = incoming.get("source", VESTA_STATION)
        try:
            msg = base64.b64decode(incoming["data"])
            send_message(source, msg)
            print(f"[mission5] {source} -> Aurora zugestellt ({len(msg)} Bytes)")
        except Exception as exc:
            print("[mission5] Fehler beim Zustellen an Aurora:", exc)

        time.sleep(SEND_PAUSE)


def run():
    start_relay_server()

    fly_to_aurora()
    threading.Thread(target=stay_in_range, daemon=True).start()

    connect(aurora_to_partner)
    partner_to_aurora()


if __name__ == "__main__":
    run()
