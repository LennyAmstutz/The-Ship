from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import auth
from Actions.cargo_commands import free_space, stone_count
from Actions.laser_commands import activate, deactivate, set_angle, state
from Actions.steering_commands import position, set_target, wait_until_in_reach
from config import (
    ANGLE_STEP,
    ARRIVAL_RADIUS,
    LASER_BURN_SECONDS,
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
        time.sleep(2)
        here = position()
        gap = _distance(here, target)
        print(f"[mission4]  {here['x']:9.1f}/{here['y']:9.1f}   noch {gap:8.1f}")
        if gap < ARRIVAL_RADIUS:
            print(f"[mission4] {label} erreicht.")
            return


class _Laser:
    """Haelt den Laser am Brennen - eine Aktivierung reicht nur ~10 Sekunden."""

    def __init__(self):
        self._last_activation = 0.0

    def keep_firing(self):
        if time.time() - self._last_activation > LASER_BURN_SECONDS:
            activate()
            self._last_activation = time.time()

    def aim(self, angle):
        set_angle(angle)


def _search_angle(laser, last_hit=None):
    candidates = list(range(0, 360, ANGLE_STEP))
    if last_hit is not None:
        candidates.sort(key=lambda a: min(abs(a - last_hit), 360 - abs(a - last_hit)))

    for angle in candidates:
        laser.keep_firing()
        laser.aim(angle)
        if state()["is_mining"]:
            return angle
        time.sleep(0.1)
    return None


def mine_stone():
    standoff = {"x": MINE_TARGET["x"] + MINING_STANDOFF, "y": MINE_TARGET["y"]}
    _fly_to(standoff, "Standoff-Punkt bei Arakrock")
    set_target("stop")
    time.sleep(1)

    laser = _Laser()
    print(f"[mission4] Suche Trefferwinkel (im Laderaum: {stone_count()} Stein) ...")
    angle = _search_angle(laser)
    if angle is None:
        raise RuntimeError(
            "Kein Trefferwinkel gefunden. Stimmt der Abstand zum Felsen? "
            "Ist der Techniker-Login erfolgreich (siehe auth.login())?"
        )
    print(f"[mission4] Treffer bei {angle} Grad, Abbau laeuft.")

    last_seen = stone_count()
    while free_space() > 0:
        laser.keep_firing()
        status = state()

        if not status["is_mining"] and not status["is_cooling_down"]:
            # Schiff gedriftet oder gedreht - Winkel neu suchen.
            new_angle = _search_angle(laser, angle)
            if new_angle is None:
                print("[mission4]  Ziel verloren, korrigiere Position ...")
                set_target(standoff)
                time.sleep(3)
                set_target("stop")
                continue
            if new_angle != angle:
                print(f"[mission4]  nachjustiert: {angle} -> {new_angle} Grad")
                angle = new_angle

        now = stone_count()
        if now != last_seen:
            print(f"[mission4]  Stein {now}")
            last_seen = now
        time.sleep(0.5)

    deactivate()
    print(f"[mission4] Laderaum voll: {stone_count()} Stein. Laser aus.")


def dock_at_vesta():
    _fly_to(VESTA_TARGET, "Vesta Station")
    wait_until_in_reach(VESTA_STATION)


def run():
    auth.login()

    if state()["kind"] != "success":
        raise RuntimeError("Laser antwortet nicht wie erwartet.")

    if free_space() > 0:
        mine_stone()
    else:
        print("[mission4] Laderaum ist bereits voll, ueberspringe den Abbau.")

    dock_at_vesta()
    print(f"[mission4] Angedockt mit {stone_count()} Stein. Mission erfuellt.")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        deactivate()
        print("\n[mission4] Abgebrochen, Laser deaktiviert.")