from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Actions import delta_sensor_commands as sensors, energy_commands
from Actions.analyzer_delta_pb import READ_CONTINUOUSLY, encode_newton_depth, encode_tachyon_data
from Actions.steering_commands import position, set_target
from grpc_server import GRPC_UNAVAILABLE, GrpcError, start_grpc_server
from config import (
    DELTA_LIMITS,
    DELTA_PORT,
    DELTA_WAIT_SECONDS,
    ENERGY_CHECK_SECONDS,
    MAGNON_ROCK,
    MAGNON_STANDOFF,
    MAGNON_STAY_RADIUS,
    MAGNON_TARGET,
    RANGE_CHECK_SECONDS,
    SENSOR_INTERVAL,
)

latest = {"newton": None, "tachyon": None}
first_data = threading.Event()
calls = {"count": 0}


def keep_power():
    """Haelt die Energielimits (auch nach Failover auf den anderen Node)."""
    last_node = None
    while True:
        try:
            node = energy_commands.active_node()
            if node != last_node:
                print(f"[delta] aktiver Energy-Node: {node}")
                last_node = node
            current = energy_commands.limits(node)
            missing = {k: v for k, v in DELTA_LIMITS.items() if current.get(k, 0) < v}
            if missing:
                print(f"[delta] Limits fehlen: {missing} - setze neu")
                print(f"[delta] Limits gesetzt auf {energy_commands.set_limits(DELTA_LIMITS)}")
        except Exception as exc:
            print("[delta] Fehler beim Energie-Check:", exc)
        time.sleep(ENERGY_CHECK_SECONDS)


def poll_newton():
    while True:
        try:
            latest["newton"] = sensors.newton_depth()
            if not first_data.is_set():
                print(f"[delta] erste Newton-Messung: {latest['newton']}")
                first_data.set()
        except Exception as exc:
            print("[delta] Newton-Sensor:", exc)
        time.sleep(SENSOR_INTERVAL)


def poll_tachyon():
    """Loest bei Bedarf das Vektoruhr-Raetsel und holt danach die Messung."""
    while True:
        try:
            status = sensors.tachyon_status()
            if status.get("kind") == "ready_to_solve":
                print("[delta] Tachyon-Log:", *status["log"], sep="\n    ")
                causes, answer = sensors.tachyon_solve(status["log"])
                print(f"[delta] Ursachen: {causes} -> Antwort: {answer}")
            latest["tachyon"] = sensors.tachyon_data()
            if latest["tachyon"] and not first_data.is_set():
                first_data.set()
        except Exception as exc:
            print("[delta] Tachyon-Scanner:", exc)
        time.sleep(SENSOR_INTERVAL)


def read_continuously(request):
    """gRPC-Stream: schickt laufend die neuesten Werte beider Sensoren an den Analyzer."""
    if not first_data.wait(DELTA_WAIT_SECONDS):
        raise GrpcError(GRPC_UNAVAILABLE, "Noch keine Sensordaten verfuegbar")
    calls["count"] += 1
    if calls["count"] == 1:
        print("[delta] Analyzer hat den Stream geoeffnet")
    while True:
        if latest["newton"]:
            yield encode_newton_depth(latest["newton"])
        if latest["tachyon"]:
            yield encode_tachyon_data(latest["tachyon"])
        time.sleep(SENSOR_INTERVAL)


def distance(a, b):
    return ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5


def hold_position(here):
    dx, dy = here["x"] - MAGNON_TARGET["x"], here["y"] - MAGNON_TARGET["y"]
    length = (dx ** 2 + dy ** 2) ** 0.5 or 1
    return {"x": MAGNON_TARGET["x"] + dx / length * MAGNON_STANDOFF,
            "y": MAGNON_TARGET["y"] + dy / length * MAGNON_STANDOFF}


def fly_and_stay():
    target = hold_position(position())
    set_target(target)
    print(f"[delta] Kurs auf {MAGNON_ROCK}, Haltepunkt {target['x']:.0f}/{target['y']:.0f}")
    arrived = False
    last_report = 0
    while True:
        try:
            here = position()
            gap = distance(here, target)
            if not arrived and gap <= MAGNON_STAY_RADIUS:
                arrived = True
                print(f"[delta] Haltepunkt beim {MAGNON_ROCK} erreicht")
            elif arrived and gap > MAGNON_STAY_RADIUS:
                print("[delta] abgedriftet, Kurs wird korrigiert")
                set_target(target)
            if time.time() - last_report >= 10:
                last_report = time.time()
                print(f"[delta] {here['x']:.1f}/{here['y']:.1f}  Abstand {gap:.1f}  "
                      f"Analyzer-Streams: {calls['count']}")
        except Exception as exc:
            print("[delta] Fehler bei Navigation:", exc)
        time.sleep(RANGE_CHECK_SECONDS)


def run():
    start_grpc_server(DELTA_PORT, {READ_CONTINUOUSLY: read_continuously})
    threading.Thread(target=keep_power, daemon=True).start()
    threading.Thread(target=poll_newton, daemon=True).start()
    threading.Thread(target=poll_tachyon, daemon=True).start()
    fly_and_stay()


if __name__ == "__main__":
    run()