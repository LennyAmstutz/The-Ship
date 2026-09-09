from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Actions.cargo_commands import hold
from Actions.laser_commands import activate, state
from Actions.steering_commands import set_target, wait_until_in_reach
from config import MINE_TARGET, STONE_AMOUNT, VESTA_STATION, VESTA_TARGET


def mine_stone():
    set_target(MINE_TARGET)
    set_angle(angle)
    activate()

    while True:
        status = hold()
        resources = status["hold"]["resources"]
        stone = resources.get("STONE", 0)
        print(f"[mission4] Stein im Hold: {stone}/{STONE_AMOUNT}")
        print(f"[mission4] Laser-Status: {state()}")

        if stone >= STONE_AMOUNT:
            break

        time.sleep(1)


def dock_at_vesta():
    set_target(VESTA_TARGET)
    wait_until_in_reach(VESTA_STATION)


def run():
    mine_stone()
    dock_at_vesta()


if __name__ == "__main__":
    run()