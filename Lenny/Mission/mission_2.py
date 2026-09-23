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
    ELYSE_STATION,
    ELYSE_TARGET,
    SHANGRIS_STATION,
    SEND_PAUSE,
    RANGE_CHECK_SECONDS,
)


def forward_to_partner(message):
    response = requests.post(command["partner_relay"], json=message, timeout=5)
    response.raise_for_status()


def fly_to_elyse():
    set_target(ELYSE_TARGET)
    print("[mission2] unterwegs zu", ELYSE_STATION)
    wait_until_in_reach(ELYSE_STATION, timeout=None)
    print("[mission2] In Reichweite von", ELYSE_STATION)


def stay_in_range():
    while True:
        try:
            if ELYSE_STATION not in stations_in_reach()["stations"]:
                print("[mission2] abgedriftet, Kurs neu setzen", flush=True)
                set_target(ELYSE_TARGET)
        except Exception as exc:
            print("[mission2] Fehler beim Reichweite-Check:", exc)
        time.sleep(RANGE_CHECK_SECONDS)


def elyse_to_partner():
    """Alles, was Elyse sendet, geht an Saskia (Shangris) weiter."""
    while True:
        message = receive_message()
        forward = {"source": ELYSE_STATION, "msg": payload(message)}
        try:
            forward_to_partner(forward)
            print("[mission2] Elyse -> Shangris weitergeleitet:", forward)
        except Exception as exc:
            print("[mission2] Fehler beim Weiterleiten an Partner:", exc)


def partner_to_elyse():
    """Nachrichten vom Partner ans eigene Comm-Modul. Staut sich etwas an,
    wird nur die neueste zugestellt - sonst wirft die Station uns raus."""
    while True:
        incoming = inbox.get()
        while not inbox.empty():
            incoming = inbox.get()

        source = incoming.get("source", SHANGRIS_STATION)
        try:
            send_message(payload(incoming), source=source)
            print("[mission2] Shangris -> Elyse zugestellt:", incoming)
        except Exception as exc:
            print("[mission2] Fehler beim Zustellen ans eigene Comm-Modul:", exc)

        time.sleep(SEND_PAUSE)


def run():
    start_relay_server()

    fly_to_elyse()
    threading.Thread(target=stay_in_range, daemon=True).start()

    connect()
    threading.Thread(target=elyse_to_partner, daemon=True).start()
    partner_to_elyse()


if __name__ == "__main__":
    run()
