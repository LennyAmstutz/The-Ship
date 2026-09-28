from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

import auth
from Actions import energy_commands, reactor_commands
from Actions.cargo_commands import count_matching, free_space, hold_size, resources
from Actions.communication_commands import sell
from Actions.laser_commands import activate, deactivate, set_angle, state
from Actions.steering_commands import position, set_target, wait_until_in_reach
from config import (
    ANALYSIS_LIMITS,
    ANGLE_STEP,
    ARRIVAL_RADIUS,
    CORE_STATION,
    CORE_TARGET,
    ENERGY_CHECK_SECONDS,
    GOLD_STANDOFF,
    GOLD_STAY_RADIUS,
    GOLD_STONE,
    GOLD_TARGET,
    LASER_POLL_SECONDS,
    MINING_LIMITS,
    MINING_STANDOFF,
    RANGE_CHECK_SECONDS,
    REACTOR_STALL_SECONDS,
    REPORT_SECONDS,
    URAN_RESOURCE,
    URAN_STONE,
    URAN_TARGET,
)

# Mission 8: Analyzer Beta beim Gold Stone laufen lassen
#   1. Laser und Kernreaktor per OAuth2 einloggen (unser OAuth-Server, wie in Mission 4)
#   2. Mit dem Laser Uran am Uran Stone abbauen, bis der Laderaum voll ist
#   3. Zum Gold Stone fliegen, dort Kernreaktor + Analyzer Beta mit Strom versorgen und bleiben
#   4. Ist das Uran verbrannt: zurueck zum Uran Stone, neues Uran holen, weiter analysieren
# Fremdes Material im Laderaum wird bei der Core Station verkauft, damit Platz fuers Uran bleibt.

wanted = {"limits": MINING_LIMITS}          # welche Limits keep_power gerade durchsetzt


# --- Energie ---------------------------------------------------------------

def apply_limits():
    """Setzt die gewuenschten Limits auf dem aktiven Node, falls sie dort nicht schon stehen."""
    node = energy_commands.active_node()
    current = energy_commands.limits(node)
    changes = {k: v for k, v in wanted["limits"].items() if abs(current.get(k, -1) - v) > 0.001}
    if changes:
        written = energy_commands.set_limits(changes)
        print(f"[mission8] Limits auf {written} gesetzt: {changes}")


def keep_power():
    """Haelt die Limits auch nach einem Failover auf den anderen Node."""
    while True:
        try:
            apply_limits()
        except Exception as exc:
            print("[mission8] Fehler beim Energie-Check:", exc)
        time.sleep(ENERGY_CHECK_SECONDS)


def switch_power(limits, label):
    wanted["limits"] = limits
    print(f"[mission8] Strom fuer {label}")
    try:
        apply_limits()
    except Exception as exc:
        print("[mission8] Limits noch nicht gesetzt (keep_power versucht es weiter):", exc)


# --- Fliegen ---------------------------------------------------------------

def _distance(a, b):
    return ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5


def _standoff_point(target, standoff):
    """Punkt `standoff` vor dem Ziel, auf der Seite, von der das Schiff kommt."""
    here = position()
    dx, dy = here["x"] - target["x"], here["y"] - target["y"]
    length = (dx ** 2 + dy ** 2) ** 0.5 or 1
    return {"x": target["x"] + dx / length * standoff, "y": target["y"] + dy / length * standoff}


def fly_to(target, label, radius=ARRIVAL_RADIUS):
    print(f"[mission8] Kurs auf {label} ({target['x']:.0f}/{target['y']:.0f}) ...")
    set_target(target)
    last_report = 0
    while True:
        here = position()
        gap = _distance(here, target)
        if gap <= radius:
            print(f"[mission8] {label} erreicht.")
            return
        if time.time() - last_report >= REPORT_SECONDS:
            last_report = time.time()
            print(f"[mission8]  {here['x']:9.1f}/{here['y']:9.1f}   noch {gap:9.1f}")
        time.sleep(RANGE_CHECK_SECONDS)


# --- Laderaum --------------------------------------------------------------

def uran_count():
    return count_matching(URAN_RESOURCE)


def sell_foreign_cargo():
    """Alles ausser Uran bei der Core Station verkaufen - sonst fehlt Platz fuers Uran."""
    foreign = {name: amount for name, amount in resources().items()
               if amount and URAN_RESOURCE.upper() not in name.upper()}
    if not foreign:
        return
    print(f"[mission8] Laderaum hat Fremdes {foreign} - verkaufe es bei {CORE_STATION}")
    set_target(CORE_TARGET)
    wait_until_in_reach(CORE_STATION, timeout=None)
    for name, amount in foreign.items():
        try:
            print(f"[mission8]  verkaufe {amount} {name}:", sell(CORE_STATION, name, amount))
        except requests.RequestException as exc:
            print(f"[mission8]  {name} konnte nicht verkauft werden:", exc)


# --- Uran abbauen ------------------------------------------------------------

def laser_login():
    """Laser per OAuth2 einloggen. Der Laser verliert seine OAuth-Config z.B. wenn er neu startet
    ("Deaktiviert (keine oauth2 Config)") - darum vor jedem Abbau und bei jedem Fehler neu."""
    try:
        auth.login("laser", interactive=False)
    except requests.RequestException as exc:
        print("[mission8] Laser-Login fehlgeschlagen:", exc)


def _laser(command, *args):
    """Laser-Befehl ausfuehren. Klappt er nicht (keine OAuth-Config, kein Login, Fehler-Antwort),
    wird der Laser neu eingeloggt und der Befehl wiederholt."""
    for attempt in range(1, 4):
        try:
            result = command(*args)
            if isinstance(result, dict) and result.get("kind", "success") != "success":
                raise ValueError(f"Antwort {result}")
            if command is state and "is_active" not in result:
                raise ValueError(f"unerwarteter Zustand {result}")
            return result
        except (requests.RequestException, ValueError) as exc:
            response = getattr(exc, "response", None)
            detail = f" ({response.status_code}: {response.text[:150]!r})" if response is not None else ""
            print(f"[mission8] Laser {command.__name__} klappt nicht: {exc}{detail} - neues Login ({attempt}/3)")
            laser_login()
            time.sleep(1)
    raise RuntimeError(f"Laser {command.__name__} klappt auch nach neuem Login nicht")


def _search_angle():
    while True:
        print("[mission8] Suche Trefferwinkel ...")
        for angle in range(0, 360, ANGLE_STEP):
            _laser(set_angle, angle)
            if not _laser(state)["is_active"]:
                _laser(activate)
            time.sleep(0.5)
            if _laser(state)["is_mining"]:
                return angle
        print(f"[mission8] Kein Winkel gefunden (Laser: {_laser(state)}) - neues Login, versuche erneut ...")
        laser_login()


def mine_uran():
    sell_foreign_cargo()
    switch_power(MINING_LIMITS, "den Laser (Reaktor und Analyzer aus)")
    fly_to(_standoff_point(URAN_TARGET, MINING_STANDOFF), f"Mining-Position vor dem {URAN_STONE}")
    laser_login()                                  # jetzt hat der Laser Strom - frisch einloggen
    time.sleep(2)

    try:
        angle = _search_angle()
        print(f"[mission8] Treffer bei {angle} Grad, Uran-Abbau laeuft.")
        while free_space() > 0:
            print(f"[mission8]  Uran {uran_count()} / {hold_size()}   Laderaum: {resources()}")
            _laser(set_angle, angle)
            status = _laser(state)
            if not status["is_active"] and not status["is_cooling_down"]:
                _laser(activate)
            time.sleep(LASER_POLL_SECONDS)
    finally:
        try:
            deactivate()
            print("[mission8] Laser aus.")
        except Exception as exc:
            print("[mission8] Laser konnte nicht deaktiviert werden:", exc)

    print(f"[mission8] Laderaum voll: {resources()}")


# --- Analyse beim Gold Stone -------------------------------------------------

def _reactor_seconds_left():
    try:
        return reactor_commands.seconds_left()
    except requests.RequestException as exc:
        print("[mission8] seconds_left nicht lesbar:", exc)
        return None


def analyze_at_gold_stone():
    """Bleibt beim Gold Stone, bis das Uran verbrannt ist."""
    hold_point = _standoff_point(GOLD_TARGET, GOLD_STANDOFF)
    fly_to(hold_point, GOLD_STONE, radius=GOLD_STAY_RADIUS)
    switch_power(ANALYSIS_LIMITS, "Kernreaktor und Analyzer Beta (Laser aus)")
    auth.login("reactor", interactive=False)      # jetzt hat der Reaktor Strom - frisch einloggen

    last_report = last_relogin = 0
    last_reading, last_change = None, time.time()  # aendert sich nichts mehr, steht der Reaktor
    while True:
        try:
            here = position()
            gap = _distance(here, hold_point)
            if gap > GOLD_STAY_RADIUS:
                print(f"[mission8] abgedriftet ({gap:.0f}), Kurs neu setzen")
                set_target(hold_point)

            uran = uran_count()
            seconds = _reactor_seconds_left()
            if time.time() - last_report >= REPORT_SECONDS:
                last_report = time.time()
                print(f"[mission8]  {here['x']:9.1f}/{here['y']:9.1f}   Uran im Laderaum: {uran}   "
                      f"Reaktor seconds_left: {seconds}")

            if uran == 0 and (seconds is None or seconds <= 0):
                print("[mission8] Uran aufgebraucht - hole neues.")
                return

            # Ein laufender Reaktor zaehlt seconds_left herunter und verbraucht Uran. Bleibt beides
            # laenger gleich (oder steht auf 0), obwohl Uran da ist, liegt es meist am Login.
            # Kurze Pausen zwischen zwei Uran-Einheiten werden so nicht als Stillstand gezaehlt.
            reading = (seconds, uran)
            if reading != last_reading and not (seconds is not None and seconds <= 0):
                last_change = time.time()
            last_reading = reading
            if (time.time() - last_change > REACTOR_STALL_SECONDS
                    and time.time() - last_relogin > REACTOR_STALL_SECONDS * 3):
                last_relogin = time.time()
                print(f"[mission8] Reaktor steht (seconds_left {seconds}, Uran {uran}) - neues Login")
                auth.login("reactor", interactive=False)
                last_change = time.time()
        except Exception as exc:
            print("[mission8] Fehler beim Analyse-Check:", exc)
        time.sleep(RANGE_CHECK_SECONDS)


def run():
    laser_login()
    try:
        auth.login("reactor", interactive=False)      # klappt evtl. erst mit Strom - dann beim Gold Stone
    except requests.RequestException as exc:
        print("[mission8] Reaktor-Login spaeter:", exc)

    threading.Thread(target=keep_power, daemon=True).start()

    while True:                                       # laeuft weiter, bis man mit Ctrl+C abbricht
        try:
            if uran_count() == 0:
                mine_uran()
                if uran_count() == 0:
                    print("[mission8] WARNUNG: kein Uran abgebaut - Laderaum:", resources())
                    continue
            analyze_at_gold_stone()
        except Exception as exc:                      # nie abstuerzen - sonst bleibt alles stehen
            print(f"[mission8] Fehler: {exc!r} - neuer Versuch in 5 s")
            time.sleep(5)


if __name__ == "__main__":
    run()
