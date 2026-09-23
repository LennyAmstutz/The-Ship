from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from Actions.comm_module_commands import connect, payload, receive_message, send_message
from Actions.communication_commands import stations_in_reach
from Actions.steering_commands import set_target, wait_until_in_reach
from relay_server import start_relay_server, inbox
from config import (
    command,
    SHANGRIS_STATION,
    SHANGRIS_TARGET,
    ELYSE_STATION,
    SEND_PAUSE,
    RANGE_CHECK_SECONDS,
)


def forward_to_partner(message):
    response = requests.post(command["partner_relay"], json=message, timeout=5)
    response.raise_for_status()


def fly_to_shangris():
    set_target(SHANGRIS_TARGET)
    print("[mission2] unterwegs zu", SHANGRIS_STATION)
    wait_until_in_reach(SHANGRIS_STATION, timeout=None)
    print("[mission2] In Reichweite von", SHANGRIS_STATION)


def stay_in_range():
    while True:
        try:
            if SHANGRIS_STATION not in stations_in_reach()["stations"]:
                print("[mission2] abgedriftet, Kurs neu setzen", flush=True)
                set_target(SHANGRIS_TARGET)
        except Exception as exc:
            print("[mission2] Fehler beim Reichweite-Check:", exc)
        time.sleep(RANGE_CHECK_SECONDS)


def shangris_to_partner():
    """Alles, was Shangris sendet, geht an Lenny (Elyse) weiter."""
    while True:
        message = receive_message()
        forward = {"source": SHANGRIS_STATION, "msg": payload(message)}
        try:
            forward_to_partner(forward)
            print("[mission2] Shangris -> Elyse weitergeleitet:", forward)
        except Exception as exc:
            print("[mission2] Fehler beim Weiterleiten an Partner:", exc)


def partner_to_shangris():
    """Nachrichten vom Partner ans eigene Comm-Modul. Staut sich etwas an,
    wird nur die neueste zugestellt - sonst wirft die Station uns raus."""
    while True:
        incoming = inbox.get()
        while not inbox.empty():
            incoming = inbox.get()

        source = incoming.get("source", ELYSE_STATION)
        try:
            send_message(payload(incoming), source=source)
            print("[mission2] Elyse -> Shangris zugestellt:", incoming)
        except Exception as exc:
            print("[mission2] Fehler beim Zustellen ans eigene Comm-Modul:", exc)

        time.sleep(SEND_PAUSE)


def run():
    start_relay_server()

    fly_to_shangris()
    threading.Thread(target=stay_in_range, daemon=True).start()

    connect()
    threading.Thread(target=shangris_to_partner, daemon=True).start()
    partner_to_shangris()


if __name__ == "__main__":
    run()
