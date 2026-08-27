from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Actions.scanner_commands import listen_for_scans
from Actions.steering_commands import set_target, wait_until_in_reach
from config import WHATSUPP_STATION, WHATSUPP_COORDINATES, WHATSUPP_DURATION


def handle_scan(data):
    print("Scan empfangen:", data)


def run():
    set_target(WHATSUPP_COORDINATES)
    wait_until_in_reach(WHATSUPP_STATION)

    print(f"[WhatsUpp] Bleibe {WHATSUPP_DURATION}s in der Nähe von {WHATSUPP_STATION}...")
    start_time = time.time()

    while time.time() - start_time < WHATSUPP_DURATION:
        time.sleep(1)

    print(f"[WhatsUpp] Mission abgeschlossen!")


if __name__ == "__main__":
    run()