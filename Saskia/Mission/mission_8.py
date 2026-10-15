
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Actions import energy_commands, void_sensor_commands
from Actions.sensor_void_energy_pb import (
    READ_DELTA_CONTINUOUSLY,
    encode_sensor_data,
)
from Actions.steering_commands import position, set_target
from grpc_server import (
    GrpcError,
    GRPC_UNAVAILABLE,
    start_grpc_server,
)
from config import (
    DELTA_LIMITS,
    DELTA_PORT,
    DELTA_WAIT_SECONDS,
    ENERGY_CHECK_SECONDS,
    SENSOR_INTERVAL,
    RANGE_CHECK_SECONDS,
    MAGNON_ROCK,
    MAGNON_TARGET,
    MAGNON_STANDOFF,
    MAGNON_STAY_RADIUS,
)

latest = {"hexdata": None}
first_measurement = threading.Event()
calls = {"count": 0}


def keep_power():
    """Stellt sicher, dass die benoetigten Energielimits gesetzt sind."""
    last_node = None

    while True:
        try:
            node = energy_commands.active_node()
            current = energy_commands.limits(node)

            missing = {
                key: value
                for key, value in DELTA_LIMITS.items()
                if current.get(key, 0) < value
            }

            if node != last_node:
                print(f"[delta] Aktiver Energy-Node: {node}")
                last_node = node

            if missing:
                print(f"[delta] Fehlende Limits: {missing}")
                written = energy_commands.set_limits(DELTA_LIMITS)
                print(f"[delta] Limits gesetzt auf {written}")

        except Exception as exc:
            print(f"[delta] Fehler bei Energieversorgung: {exc}")

        time.sleep(ENERGY_CHECK_SECONDS)


def measure_forever():
    """Holt fortlaufend Messungen vom Vakuumenergiesensor."""
    counter = 0

    while True:
        counter += 1
        request_id = f"delta_{int(time.time())}_{counter:04d}"

        try:
            data = void_sensor_commands.measure(request_id)
            latest["hexdata"] = data

            if not first_measurement.is_set():
                print(f"[delta] Erste Messung erhalten: {data}")
                first_measurement.set()

        except Exception as exc:
            print(f"[delta] Fehler bei Messung: {exc}")

        time.sleep(SENSOR_INTERVAL)


def read_sensor_data(request):
    """Beantwortet eine gRPC-Anfrage des Analyzers."""
    if not first_measurement.wait(DELTA_WAIT_SECONDS):
        raise GrpcError(
            GRPC_UNAVAILABLE,
            "Noch keine Sensordaten verfuegbar",
        )

    calls["count"] += 1

    data = latest["hexdata"]

    if data is None:
        raise GrpcError(
            GRPC_UNAVAILABLE,
            "Sensordaten sind nicht verfuegbar",
        )

    if calls["count"] == 1:
        print("[delta] Analyzer hat die ersten Sensordaten abgefragt")

    return encode_sensor_data(data)


def distance(a, b):
    dx = a["x"] - b["x"]
    dy = a["y"] - b["y"]
    return (dx ** 2 + dy ** 2) ** 0.5


def hold_position(here):
    """Berechnet einen Haltepunkt vor dem Magnon Rock."""
    dx = here["x"] - MAGNON_TARGET["x"]
    dy = here["y"] - MAGNON_TARGET["y"]

    length = (dx ** 2 + dy ** 2) ** 0.5

    if length == 0:
        return {
            "x": MAGNON_TARGET["x"] + MAGNON_STANDOFF,
            "y": MAGNON_TARGET["y"],
        }

    return {
        "x": MAGNON_TARGET["x"] + dx / length * MAGNON_STANDOFF,
        "y": MAGNON_TARGET["y"] + dy / length * MAGNON_STANDOFF,
    }


def fly_and_stay():
    here = position()
    target = hold_position(here)

    set_target(target)

    print(
        f"[delta] Flug zum {MAGNON_ROCK}: "
        f"{MAGNON_TARGET['x']}/{MAGNON_TARGET['y']}"
    )
    print(
        f"[delta] Haltepunkt: "
        f"{target['x']:.0f}/{target['y']:.0f}"
    )

    arrived = False
    last_report = 0

    while True:
        try:
            here = position()
            gap = distance(here, target)

            if not arrived and gap <= MAGNON_STAY_RADIUS:
                arrived = True
                print(
                    f"[delta] Haltepunkt beim {MAGNON_ROCK} erreicht"
                )

            elif arrived and gap > MAGNON_STAY_RADIUS:
                print("[delta] Schiff abgedriftet, Kurs wird korrigiert")
                set_target(target)

            if time.time() - last_report >= 10:
                last_report = time.time()
                print(
                    f"[delta] Position {here['x']:.1f}/{here['y']:.1f}; "
                    f"Abstand zum Haltepunkt {gap:.1f}; "
                    f"gRPC-Aufrufe {calls['count']}"
                )

        except Exception as exc:
            print(f"[delta] Fehler bei Navigation: {exc}")

        time.sleep(RANGE_CHECK_SECONDS)


def run():
    start_grpc_server(
    DELTA_PORT,
    {READ_DELTA_CONTINUOUSLY: read_sensor_data},
    )

    threading.Thread(
        target=keep_power,
        daemon=True,
    ).start()

    threading.Thread(
        target=measure_forever,
        daemon=True,
    ).start()

    fly_and_stay()


if __name__ == "__main__":
    run()
