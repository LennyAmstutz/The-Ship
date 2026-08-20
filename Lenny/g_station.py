"""
G-Station 1-5 abfangen und 60s in der Naehe bleiben.

Nutzt config.py und travel.py aus diesem Projekt.
RabbitMQ laeuft lokal auf dieser VM -> host = localhost, port 2014.

Starten:  python3 g_station.py
"""

import json
import threading
import time

import pika
import requests

import config as cfg
import travel as t

# --- anpassen falls noetig -------------------------------------------------
RABBIT_HOST = "localhost"
RABBIT_PORT = 2014
EIGENES_SCHIFF = cfg.HOST            # "192.168.101.50" -> eigenes Schiff filtern

STATION_NAME = "G-Station 1-5"
TREFFPUNKT_X, TREFFPUNKT_Y = -19747, -14282
ZIEL_SEKUNDEN = 60
TOLERANZ = 100                        # wie nah an den Treffpunkt bevor gewartet wird
# ---------------------------------------------------------------------------

EXCHANGE = "scanner/detected_objects"
POS_URL = f"http://{cfg.HOST}:2010/pos"
ENERGY_URLS = [f"http://{cfg.HOST}:2032/limits", f"http://{cfg.HOST}:2033/limits"]

letzte_position = None
lock = threading.Lock()


# --- Energie ---------------------------------------------------------------

def setze_energie(limits):
    for url in ENERGY_URLS:
        try:
            requests.put(url, json=limits, timeout=cfg.TIMEOUT)
        except Exception as e:
            print("Energie", url, "fehlgeschlagen:", e)


def fliegen_ein():
    """Thruster und vor allem der Scanner brauchen Energie."""
    setze_energie({
        "laser": 0,
        "cargo_bot": 0,
        "laser_amplifier": 0,
        "sensor_plasma_radiation": 0,
        "thruster_back": 1,
        "thruster_front": 1,
        "thruster_front_left": 1,
        "thruster_front_right": 1,
        "thruster_bottom_left": 1,
        "thruster_bottom_right": 1,
        "scanner": 1,
        "sensor_atomic_field": 0,
        "matter_stabilizer": 0,
        "nuclear_reactor": 0,
        "sensor_void_energy": 0,
        "shield_generator": 0,
    })


# --- Navigation ------------------------------------------------------------

def position():
    return requests.get(POS_URL, timeout=cfg.TIMEOUT).json()["pos"]


def fly_to_pos(x, y):
    """Ziel setzen und warten, bis wir dort sind."""
    t.set_target({"x": x, "y": y})
    while True:
        p = position()
        if abs(p["x"] - x) < TOLERANZ and abs(p["y"] - y) < TOLERANZ:
            break
        time.sleep(1)
    print(f"Position erreicht: {x}/{y}")


def ist_in_reichweite():
    try:
        s = t.stations() or {}
        return any(STATION_NAME.lower() in name.lower() for name in s)
    except Exception as e:
        print("stations_in_reach fehlgeschlagen:", e)
        return False


# --- Scanner / RabbitMQ ----------------------------------------------------

def consume(handle_station):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBIT_HOST, port=RABBIT_PORT)
    )
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="fanout")
    result = channel.queue_declare(queue="", exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange=EXCHANGE, queue=queue_name)
    print("mit RabbitMQ verbunden, warte auf Scans...")

    for method_frame, properties, body in channel.consume(queue=queue_name, auto_ack=True):
        for station in json.loads(body.decode("utf-8")):
            if station["name"] != EIGENES_SCHIFF:
                handle_station(station)


def handle_station(station):
    global letzte_position
    name = str(station.get("name", ""))
    print("gescannt:", name)

    if STATION_NAME.lower() in name.lower():
        pos = (float(station["pos"]["x"]), float(station["pos"]["y"]))
        with lock:
            letzte_position = pos
        print(">>> GEFUNDEN:", name, pos)


# --- Hauptablauf -----------------------------------------------------------

def main():
    fliegen_ein()
    fly_to_pos(TREFFPUNKT_X, TREFFPUNKT_Y)
    print("am Treffpunkt, warte auf", STATION_NAME)

    threading.Thread(target=consume, args=(handle_station,), daemon=True).start()

    sekunden = 0
    zuletzt_verfolgt = None

    while sekunden < ZIEL_SEKUNDEN:
        with lock:
            pos = letzte_position

        if pos and pos != zuletzt_verfolgt:      # Station bewegt sich -> nachziehen
            t.set_target({"x": pos[0], "y": pos[1]})
            zuletzt_verfolgt = pos

        if ist_in_reichweite():
            sekunden += 1
            print("in Reichweite:", sekunden, "/", ZIEL_SEKUNDEN)
        else:
            if sekunden:
                print("Kontakt verloren, Zaehler zurueck auf 0")
            sekunden = 0

        time.sleep(1)

    print("Geschafft:", ZIEL_SEKUNDEN, "Sekunden bei", STATION_NAME)


if __name__ == "__main__":
    main()