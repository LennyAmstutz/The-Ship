from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from Actions.comm_module_commands import connect, receive_message, send_message
from Actions.communication_commands import stations_in_reach
from Actions.steering_commands import set_target, wait_until_in_reach
from relay_server import start_relay_server, inbox
from config import (
    command,
    ELYSE_STATION,
    SHANGRIS_STATION,
    SHANGRIS_TARGET,
    MISSION2_MAX_GAP,
    MISSION2_HOLD_SECONDS,
)


def forward_to_partner(message):
    response = requests.post(command["partner_relay"], json=message, timeout=5)
    response.raise_for_status()


def listen_own_module():
    connect()
    while True:
        try:
            message = receive_message()
        except Exception as exc:
            print("[mission2] Fehler beim Empfangen vom eigenen Comm-Modul:", exc)
            time.sleep(1)
            continue

        print("[mission2] Vom eigenen Comm-Modul erhalten:", message)
        if message.get("destination") == ELYSE_STATION:
            try:
                forward_to_partner(message)
                print("[mission2] Shangris -> Elyse weitergeleitet:", message)
            except Exception as exc:
                print("[mission2] Fehler beim Weiterleiten an Partner:", exc)


def run():
    start_relay_server()

    set_target(SHANGRIS_TARGET)
    wait_until_in_reach(SHANGRIS_STATION, timeout=None)
    print("[mission2] In Reichweite von", SHANGRIS_STATION)

    threading.Thread(target=listen_own_module, daemon=True).start()

    started = time.monotonic()

    while True:
        try:
            stations = stations_in_reach().get("stations", [])
            if SHANGRIS_STATION not in stations:
                print(f"[mission2] WARNUNG: nicht mehr in Reichweite von {SHANGRIS_STATION}! stations={stations} -> Ziel neu setzen")
                set_target(SHANGRIS_TARGET)
            else:
                print(f"[mission2] Reichweite ok, in stations={stations}")
        except Exception as exc:
            print("[mission2] Fehler beim Reichweite-Check:", exc)

        while not inbox.empty():
            incoming = inbox.get()
            payload = incoming.get("msg", incoming.get("data"))
            try:
                send_message(payload, destination=SHANGRIS_STATION)
                print("[mission2] Elyse -> Shangris zugestellt:", incoming)
            except Exception as exc:
                print("[mission2] Fehler beim Zustellen ans eigene Comm-Modul:", exc)

        elapsed = time.monotonic() - started
        print(f"[mission2] laeuft seit {elapsed:.1f}s (Ziel: {MISSION2_HOLD_SECONDS}s am Stueck)")

        time.sleep(max(0.5, MISSION2_MAX_GAP - 2))


if __name__ == "__main__":
    run()