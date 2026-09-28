from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Actions import energy_commands, void_sensor_commands
from Actions.mongo_client import MongoClient
from Actions.communication_commands import stations_in_reach
from Actions.steering_commands import position, set_target
from mongo_server import start_mongo_server
from config import (
    ENERGY_CHECK_SECONDS,
    MONGO_DB,
    MONGO_HOST,
    MONGO_PASSWORD,
    MONGO_PORT,
    MONGO_USER,
    RELIEF_STATION,
    RELIEF_TARGET,
    SENSOR_INTERVAL,
    SHIELD_LIMITS,
    VACUUM_COLLECTION,
)

mongo = MongoClient(MONGO_HOST, MONGO_PORT, MONGO_USER, MONGO_PASSWORD, MONGO_DB)
first_measurement = threading.Event()


def power_shield():
    node = energy_commands.set_limits(SHIELD_LIMITS)
    print(f"[mission6] Strom fuer Sensor und Schild auf {node} gesetzt: {SHIELD_LIMITS}")


def keep_power():
    last_node = None
    while True:
        try:
            node = energy_commands.active_node()
            current = energy_commands.limits(node)
            missing = {k: v for k, v in SHIELD_LIMITS.items() if current.get(k, 0) < v}
            if node != last_node:
                print(f"[mission6] aktiver Energy-Node: {node}")
                last_node = node
            if missing:
                print(f"[mission6] Limits fehlen auf {node}: {missing} - setze neu")
                power_shield()
        except Exception as exc:
            print("[mission6] Fehler beim Energie-Check:", exc)
        time.sleep(ENERGY_CHECK_SECONDS)


def store_measurement(data):
    """Genau ein Dokument { "data": "<hex>" } in vacuum-energy - das alte wird ersetzt."""
    if len(mongo.find(VACUUM_COLLECTION)) > 1:
        mongo.delete_many(VACUUM_COLLECTION)
    mongo.replace_one(VACUUM_COLLECTION, {}, {"data": data}, upsert=True)


def measure_forever():
    counter = 0
    while True:
        counter += 1
        request_id = f"lenny_{int(time.time())}_{counter:04d}"
        try:
            data = void_sensor_commands.measure(request_id)
            store_measurement(data)
            if not first_measurement.is_set():
                print(f"[mission6] erste Messung in MongoDB: {data}")
                first_measurement.set()
            else:
                print(f"[mission6] Messung {request_id}: {data}")
        except Exception as exc:
            print(f"[mission6] Fehler bei Messung {request_id}:", exc)
        time.sleep(SENSOR_INTERVAL)


def fly_to_relief():
    set_target(RELIEF_TARGET)
    print(f"[mission6] Kurs auf {RELIEF_STATION} ({RELIEF_TARGET['x']}/{RELIEF_TARGET['y']})")
    while RELIEF_STATION not in stations_in_reach()["stations"]:
        here = position()
        gap = ((here["x"] - RELIEF_TARGET["x"]) ** 2 + (here["y"] - RELIEF_TARGET["y"]) ** 2) ** 0.5
        print(f"[mission6]  {here['x']:9.1f}/{here['y']:9.1f}   noch {gap:9.1f}")
        time.sleep(5)
    print(f"[mission6] In Reichweite von {RELIEF_STATION}. Mission erfuellt.")


def run():
    start_mongo_server()

    threading.Thread(target=keep_power, daemon=True).start()
    threading.Thread(target=measure_forever, daemon=True).start()

    print("[mission6] warte auf die erste Sensor-Messung ...")
    first_measurement.wait()

    fly_to_relief()

    while True:
        time.sleep(60)


if __name__ == "__main__":
    run()
