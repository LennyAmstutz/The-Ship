from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from Actions.vesta_commands import connect, send_message
from Actions.communication_commands import stations_in_reach
from Actions.steering_commands import set_target, wait_until_in_reach
from mqtt_broker import start_mqtt_broker
from relay_server import start_relay_server, inbox
from config import (
    command,
    AURORA_STATION,
    VESTA_STATION,
    VESTA_TARGET,
    SEND_PAUSE,
    RANGE_CHECK_SECONDS,
)


def forward_to_partner(message):
    response = requests.post(command["partner_relay"], json=message, timeout=5)
    response.raise_for_status()


def fly_to_vesta():
    set_target(VESTA_TARGET)
    print("[mission5] unterwegs zu", VESTA_STATION)
    wait_until_in_reach(VESTA_STATION, timeout=None)
    print("[mission5] In Reichweite von", VESTA_STATION)


def stay_in_range():
    while True:
        try:
            if VESTA_STATION not in stations_in_reach()["stations"]:
                print("[mission5] abgedriftet, Kurs neu setzen", flush=True)
                set_target(VESTA_TARGET)
        except Exception as exc:
            print("[mission5] Fehler beim Reichweite-Check:", exc)
        time.sleep(RANGE_CHECK_SECONDS)


def vesta_to_partner(message):
    """Vesta publisht {"dst": ..., "data": base64} - geht an Saskia (Aurora) weiter.
    Zwischen den Schiffen bleibt data base64, damit die Binaerdaten in JSON passen."""
    forward = {"source": VESTA_STATION, "data": message["data"]}
    try:
        forward_to_partner(forward)
        print(f"[mission5] Vesta -> {message.get('dst')} weitergeleitet:", forward)
    except Exception as exc:
        print("[mission5] Fehler beim Weiterleiten an Partner:", exc)


def partner_to_vesta():
    """Nachrichten vom Partner an Vesta. Staut sich etwas an, nur die neueste."""
    while True:
        incoming = inbox.get()
        while not inbox.empty():
            incoming = inbox.get()

        source = incoming.get("source", AURORA_STATION)
        try:
            send_message(source, incoming["data"])
            print(f"[mission5] {source} -> Vesta zugestellt:", incoming)
        except Exception as exc:
            print("[mission5] Fehler beim Zustellen an Vesta:", exc)

        time.sleep(SEND_PAUSE)


def run():
    start_relay_server()
    start_mqtt_broker()    # das Comm-Modul erwartet den MQTT-Server auf diesem Schiff

    fly_to_vesta()
    threading.Thread(target=stay_in_range, daemon=True).start()

    connect(vesta_to_partner)
    partner_to_vesta()


if __name__ == "__main__":
    run()
