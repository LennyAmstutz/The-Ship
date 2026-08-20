import json
import threading
import time

import pika
import requests

import communication as c
import energy_management as em
import travel as t

# --- anpassen falls noetig -------------------------------------------------
RABBIT_HOST = "localhost"
RABBIT_PORT = 2014
EIGENES_SCHIFF = "192.168.101.50"

STATION_NAME = "G-Station 1-5"
TREFFPUNKT_X, TREFFPUNKT_Y = -19747, -14282
ZIEL_SEKUNDEN = 60
# ---------------------------------------------------------------------------

EXCHANGE = "scanner/detected_objects"
SET_TARGET_URL = "http://10.255.255.254:2009/set_target"

letzte_position = None
lock = threading.Lock()


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


def setze_ziel(x, y):
    try:
        requests.post(SET_TARGET_URL, json={"target": {"x": x, "y": y}}, timeout=5)
    except Exception as e:
        print("set_target fehlgeschlagen:", e)


def ist_in_reichweite():
    try:
        stations = c.get_near_station().json().get("stations") or {}
        return any(STATION_NAME.lower() in s.lower() for s in stations)
    except Exception as e:
        print("stations_in_reach fehlgeschlagen:", e)
        return False


def main():
    em.fliegen_ein()
    t.travel_position_until_recive(TREFFPUNKT_X, TREFFPUNKT_Y)
    print("am Treffpunkt, warte auf", STATION_NAME)

    threading.Thread(target=consume, args=(handle_station,), daemon=True).start()

    sekunden = 0
    zuletzt_verfolgt = None

    while sekunden < ZIEL_SEKUNDEN:
        with lock:
            pos = letzte_position

        if pos and pos != zuletzt_verfolgt:
            setze_ziel(pos[0], pos[1])
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
