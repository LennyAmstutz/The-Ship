from pathlib import Path
import sys
import threading
import time

from config import HINT, HOLD_SECONDS, WHATSUPP_STATION

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Actions.communication_commands import stations_in_reach
from Actions.scanner_commands import detected_objects
from Actions.steering_commands import set_target

station_pos = None


def watch_scanner():
    global station_pos
    for objects in detected_objects():
        print("Scan empfangen:", objects)
        for obj in objects:
            if obj.get("name") == WHATSUPP_STATION:
                station_pos = obj["pos"]
                print("Station gefunden:", station_pos)


def run():
    threading.Thread(target=watch_scanner, daemon=True).start()

    in_reach_since = None

    while True:
        target = station_pos if station_pos else HINT
        print("Sende Ziel:", target, "| station_pos:", station_pos)
        result = set_target(target)
        print("Antwort set_target:", result)

        if WHATSUPP_STATION in stations_in_reach()["stations"]:
            if in_reach_since is None:
                in_reach_since = time.monotonic()
            held = time.monotonic() - in_reach_since
            print(f"[mission3] in reach seit {held:.1f}s / {HOLD_SECONDS}s")
        else:
            in_reach_since = None
            held = 0

        if held >= HOLD_SECONDS:
            print("[mission3] Ziel erreicht - lange genug bei der Station geblieben.")
            break

        time.sleep(0.5)


if __name__ == "__main__":
    run()