from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import auth
from Actions.cargo_commands import free_space, hold_size, stone_count
from Actions.laser_commands import activate, deactivate, set_angle, state
from Actions.steering_commands import position, set_target, wait_until_in_reach
from config import (
    ANGLE_STEP,
    ARRIVAL_RADIUS,
    LASER_POLL_SECONDS,
    MINE_TARGET,
    MINING_STANDOFF,
    VESTA_STATION,
    VESTA_TARGET,
)


def _distance(a, b):
    return ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5


def _fly_to(target, label):
    print(f"[mission4] Kurs auf {label} ({target['x']:.0f}/{target['y']:.0f}) ...")
    set_target(target)
    while True:
        here = position()
        gap = _distance(here, target)
        print(f"[mission4]  {here['x']:9.1f}/{here['y']:9.1f}   noch {gap:8.1f}")
        if gap <= ARRIVAL_RADIUS:
            print(f"[mission4] {label} erreicht.")
            return
        time.sleep(2)


def _mining_position(here):
    """Punkt MINING_STANDOFF vor Arakrock, auf der Seite, von der das Schiff kommt."""
    dx = here["x"] - MINE_TARGET["x"]
    dy = here["y"] - MINE_TARGET["y"]
    length = (dx ** 2 + dy ** 2) ** 0.5
    if length == 0:
        return {"x": MINE_TARGET["x"], "y": MINE_TARGET["y"] - MINING_STANDOFF}
    return {
        "x": MINE_TARGET["x"] + dx / length * MINING_STANDOFF,
        "y": MINE_TARGET["y"] + dy / length * MINING_STANDOFF,
    }


def _search_angle():
    while True:
        print("[mission4] Suche Trefferwinkel ...")
        for angle in range(0, 360, ANGLE_STEP):
            set_angle(angle)
            if not state()["is_active"]:
                activate()
            time.sleep(0.5)
            if state()["is_mining"]:
                return angle
        print("[mission4] Kein Winkel gefunden, versuche erneut ...")


def mine_stone():
    target = _mining_position(position())
    _fly_to(target, "Mining-Position vor Arakrock")
    time.sleep(3)
    print(f"[mission4] Abstand zu Arakrock: {_distance(position(), MINE_TARGET):.1f}")

    try:
        angle = _search_angle()
        print(f"[mission4] Treffer bei {angle} Grad, Abbau laeuft.")

        while free_space() > 0:
            print(f"[mission4]  Stein {stone_count()} / {hold_size()}")

            set_angle(angle)
            status = state()
            if status["is_mining"]:
                print("[mission4]  Laser baut Stein ab")
            elif status["is_cooling_down"]:
                print("[mission4]  Laser kuehlt ab")
            elif not status["is_active"]:
                print("[mission4]  Laser wird aktiviert ...")
                activate()

            time.sleep(LASER_POLL_SECONDS)
    finally:
        try:
            deactivate()
            print("[mission4] Laser aus.")
        except Exception as exc:
            print("[mission4] Laser konnte nicht deaktiviert werden:", exc)

    print(f"[mission4] Laderaum voll: {stone_count()} Stein.")


def dock_at_vesta():
    _fly_to(VESTA_TARGET, VESTA_STATION)
    wait_until_in_reach(VESTA_STATION)


def run():
    auth.login()

    if free_space() > 0:
        mine_stone()
    else:
        print("[mission4] Laderaum ist bereits voll, ueberspringe den Abbau.")

    dock_at_vesta()
    print(f"[mission4] Angedockt bei {VESTA_STATION} mit {stone_count()} Stein. Mission erfuellt.")


if __name__ == "__main__":
    run()
