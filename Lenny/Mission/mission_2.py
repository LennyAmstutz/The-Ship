from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from Actions.comm_module_commands import connect, receive_message, send_message
from Actions.steering_commands import set_target, wait_until_in_reach
from relay_server import start_relay_server, inbox
from config import (
    command,
    ELYSE_STATION,
    ELYSE_TARGET,
    SHANGRIS_STATION,
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
        if message.get("destination") == SHANGRIS_STATION:
            try:
                forward_to_partner(message)
                print("[mission2] Elyse -> Shangris weitergeleitet:", message)
            except Exception as exc:
                print("[mission2] Fehler beim Weiterleiten an Partner:", exc)


def run():
    start_relay_server()

    set_target(ELYSE_TARGET)
    wait_until_in_reach(ELYSE_STATION, timeout=None)
    print("[mission2] In Reichweite von", ELYSE_STATION)

    threading.Thread(target=listen_own_module, daemon=True).start()

    started = time.monotonic()

    while True:
        while not inbox.empty():
            incoming = inbox.get()
            try:
                send_message(incoming.get("msg"), destination=ELYSE_STATION)
                print("[mission2] Shangris -> Elyse zugestellt:", incoming)
            except Exception as exc:
                print("[mission2] Fehler beim Zustellen ans eigene Comm-Modul:", exc)

        elapsed = time.monotonic() - started
        print(f"[mission2] laeuft seit {elapsed:.1f}s (Ziel: {MISSION2_HOLD_SECONDS}s am Stueck)")

        time.sleep(max(0.5, MISSION2_MAX_GAP - 2))


if __name__ == "__main__":
    run()