"""Dauerschleife: Eisen bei der Kauf-Station kaufen, zur Verkaufs-Station fliegen, alles verkaufen, wiederholen.

Starten:  python3 Mission/mission_trade.py   (oder in main.py:  from Mission.mission_trade import run; run())
Beenden:  Strg+C
Nicht gleichzeitig mit einer anderen Mission laufen lassen - beide wuerden das Schiff steuern.
"""
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from Actions.cargo_commands import hold
from Actions.communication_commands import buy, sell
from Actions.steering_commands import set_target, wait_until_in_reach
from config import BUY_STATION, RESOURCE, SELL_STATION

REACH_TIMEOUT = 600      # Sekunden, die der Flug zu einer Station dauern darf
ERROR_PAUSE = 5          # Pause nach einem Fehler
NO_MONEY_PAUSE = 10      # Pause, wenn nicht mal 1 Stueck gekauft werden kann

stats = {"cycles": 0, "bought": 0, "sold": 0}


def iron_in_hold():
    return hold()["hold"]["resources"].get(RESOURCE, 0)


def free_space():
    return hold()["hold"]["hold_free"]


def go_to(station):
    print(f"[trade] Kurs auf {station} ...")
    set_target(station)
    wait_until_in_reach(station, timeout=REACH_TIMEOUT)
    print(f"[trade] {station} in Reichweite")


def buy_max(station):
    """Kauft so viel wie in den Laderaum passt. Reicht das Geld nicht, wird die Menge halbiert."""
    amount = free_space()
    while amount >= 1:
        try:
            buy(station, RESOURCE, amount)
            stats["bought"] += amount
            print(f"[trade] {amount} {RESOURCE} gekauft")
            return amount
        except requests.HTTPError as exc:
            body = exc.response.text.strip()[:150] if exc.response is not None else exc
            print(f"[trade] Kauf von {amount} abgelehnt: {body}")
            amount //= 2
    return 0


def sell_all(station):
    amount = iron_in_hold()
    if amount <= 0:
        return 0
    sell(station, RESOURCE, amount)
    stats["sold"] += amount
    print(f"[trade] {amount} {RESOURCE} verkauft")
    return amount


def run():
    print(f"[trade] Handel mit {RESOURCE}: kaufen bei {BUY_STATION}, verkaufen bei {SELL_STATION}")
    while True:
        try:
            if iron_in_hold() > 0:          # z.B. nach einem Abbruch noch Ware an Bord
                go_to(SELL_STATION)
                sell_all(SELL_STATION)

            go_to(BUY_STATION)
            if buy_max(BUY_STATION) == 0:
                print(f"[trade] Nichts kaufbar (Geld oder Platz), warte {NO_MONEY_PAUSE}s")
                time.sleep(NO_MONEY_PAUSE)
                continue

            go_to(SELL_STATION)
            sell_all(SELL_STATION)

            stats["cycles"] += 1
            print(f"[trade] Runde {stats['cycles']} fertig "
                  f"(gekauft {stats['bought']}, verkauft {stats['sold']}) - Laderaum: {hold()['hold']}")
        except KeyboardInterrupt:
            print("[trade] Abbruch durch Benutzer")
            return
        except Exception as exc:
            print(f"[trade] Fehler: {exc!r} - weiter in {ERROR_PAUSE}s")
            time.sleep(ERROR_PAUSE)


if __name__ == "__main__":
    run()