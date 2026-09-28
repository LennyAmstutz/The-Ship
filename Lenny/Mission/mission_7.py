from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Actions import energy_commands, void_sensor_commands
from Actions.sensor_void_energy_pb import READ_SENSOR_DATA, encode_sensor_data
from Actions.steering_commands import position, set_target
from grpc_server import GrpcError, GRPC_UNAVAILABLE, start_grpc_server
from config import (
    ANALYZER_LIMITS,
    ENERGY_CHECK_SECONDS,
    GRPC_PORT,
    GRPC_WAIT_SECONDS,
    RANGE_CHECK_SECONDS,
    SENSOR_INTERVAL,
    URAN_STANDOFF,
    URAN_STAY_RADIUS,
    URAN_STONE,
    URAN_TARGET,
)

# Mission 7: Analyzer Alpha
#   1. Energy-Management: Sensor und Analyzer auf dem aktiven Node mit Strom versorgen
#   2. gRPC-Server auf Port 2102 betreiben - dort holt der Analyzer die Sensordaten ab
#   3. Vakuumenergie-Sensor messen lassen und die Messung danach wieder loeschen
#   4. Zum Uran Stone fliegen und in der Naehe bleiben, bis die Analyse fertig ist

latest = {"hexdata": None}
first_measurement = threading.Event()
calls = {"count": 0}


def keep_power():
    """Wechselt der aktive Node (Failover) oder werden die Limits zurueckgesetzt, neu setzen."""
    last_node = None
    while True:
        try:
            node = energy_commands.active_node()
            current = energy_commands.limits(node)
            missing = {k: v for k, v in ANALYZER_LIMITS.items() if current.get(k, 0) < v}
            if node != last_node:
                print(f"[mission7] aktiver Energy-Node: {node}")
                last_node = node
            if missing:
                print(f"[mission7] Limits fehlen auf {node}: {missing} - setze neu")
                written = energy_commands.set_limits(ANALYZER_LIMITS)
                print(f"[mission7] Strom fuer Sensor und Analyzer auf {written} gesetzt")
        except Exception as exc:
            print("[mission7] Fehler beim Energie-Check:", exc)
        time.sleep(ENERGY_CHECK_SECONDS)


def measure_forever():
    counter = 0
    while True:
        counter += 1
        request_id = f"lenny_m7_{int(time.time())}_{counter:04d}"
        try:
            latest["hexdata"] = void_sensor_commands.measure(request_id)   # loescht die Messung danach
            if not first_measurement.is_set():
                print(f"[mission7] erste Messung: {latest['hexdata']}")
                first_measurement.set()
        except Exception as exc:
            print(f"[mission7] Fehler bei Messung {request_id}:", exc)
        time.sleep(SENSOR_INTERVAL)


def read_sensor_data(request):
    """gRPC: rpc read_sensor_data(Void) returns (SensorData) - gibt die neueste Messung zurueck."""
    if not first_measurement.wait(GRPC_WAIT_SECONDS):
        raise GrpcError(GRPC_UNAVAILABLE, "noch keine Sensordaten")
    calls["count"] += 1
    if calls["count"] == 1:
        print(f"[mission7] Analyzer holt die ersten Sensordaten ab: {latest['hexdata']}")
    return encode_sensor_data(latest["hexdata"])


def _distance(a, b):
    return ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5


def _hold_position(here):
    """Punkt URAN_STANDOFF vor dem Uran Stone, auf der Seite, von der das Schiff kommt."""
    dx, dy = here["x"] - URAN_TARGET["x"], here["y"] - URAN_TARGET["y"]
    length = (dx ** 2 + dy ** 2) ** 0.5 or 1
    return {"x": URAN_TARGET["x"] + dx / length * URAN_STANDOFF,
            "y": URAN_TARGET["y"] + dy / length * URAN_STANDOFF}


def fly_and_stay():
    target = _hold_position(position())
    set_target(target)
    print(f"[mission7] Kurs auf {URAN_STONE} ({URAN_TARGET['x']}/{URAN_TARGET['y']}), "
          f"Halte-Punkt {target['x']:.0f}/{target['y']:.0f}")
    arrived = False
    last_report = 0
    while True:
        try:
            here = position()
            gap = _distance(here, target)
            if not arrived and gap <= URAN_STAY_RADIUS:
                arrived = True
                print(f"[mission7] beim {URAN_STONE} angekommen - bleibe hier, Analyzer laeuft")
            elif arrived and gap > URAN_STAY_RADIUS:
                print(f"[mission7] abgedriftet ({gap:.0f}), Kurs neu setzen")
                set_target(target)
            if time.time() - last_report >= 10:
                last_report = time.time()
                print(f"[mission7]  {here['x']:9.1f}/{here['y']:9.1f}   noch {gap:8.1f}   "
                      f"gRPC-Aufrufe vom Analyzer: {calls['count']}")
        except Exception as exc:
            print("[mission7] Fehler beim Positions-Check:", exc)
        time.sleep(RANGE_CHECK_SECONDS)


def run():
    start_grpc_server(GRPC_PORT, {READ_SENSOR_DATA: read_sensor_data})

    threading.Thread(target=keep_power, daemon=True).start()
    threading.Thread(target=measure_forever, daemon=True).start()

    fly_and_stay()          # laeuft weiter, bis man mit Ctrl+C abbricht


if __name__ == "__main__":
    run()
