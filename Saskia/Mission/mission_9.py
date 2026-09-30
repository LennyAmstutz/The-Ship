from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Actions import antimatter_sensor_commands, energy_commands, s3_client
from Actions.steering_commands import position, set_target
from s3_server import start_s3_server
from config import (
    AETHERIUM_ROCK,
    AETHERIUM_STANDOFF,
    AETHERIUM_STAY_RADIUS,
    AETHERIUM_TARGET,
    ANTIMATTER_INTERVAL,
    ENERGY_CHECK_SECONDS,
    GAMMA_LIMITS,
    RANGE_CHECK_SECONDS,
    REPORT_SECONDS,
    S3_BUCKET,
    S3_OBJECT,
    S3_PORT,
)

# Mission 9: Analyzer Gamma beim Aetherium Rock laufen lassen
#   1. Eigenen S3-Server auf Port 2016 starten (Bucket analyzer-gamma, theship / theship1234)
#      - Saskia: der Analyzer sucht ihn unter http://192.168.101.51:2016
#   2. Energy-Management: Antimateriesensor und Analyzer Gamma mit Strom versorgen
#   3. Antimateriesensor messen lassen - x, y und z GLEICHZEITIG (3 Threads) - und das Resultat
#      als Hex-String in s3://analyzer-gamma/data.hex hochladen. Der Analyzer liest es dort regelmaessig.
#   4. Zum Aetherium Rock (30957/-28933) fliegen und in der Naehe bleiben
# Nebenlaeufig: Energie-Check, Messen+Hochladen und Fliegen laufen in eigenen Threads,
# der S3-Server beantwortet jede Anfrage des Analyzers in einem eigenen Thread.

stats = {"uploads": 0, "last": None}
first_upload = threading.Event()


def keep_power():
    """Haelt die Limits auch nach einem Failover auf den anderen Node."""
    last_node = None
    while True:
        try:
            node = energy_commands.active_node()
            if node != last_node:
                print(f"[mission9] aktiver Energy-Node: {node}")
                last_node = node
            current = energy_commands.limits(node)
            changes = {k: v for k, v in GAMMA_LIMITS.items() if abs(current.get(k, -1) - v) > 0.001}
            if changes:
                written = energy_commands.set_limits(changes)
                print(f"[mission9] Limits auf {written} gesetzt: {changes}")
        except Exception as exc:
            print("[mission9] Fehler beim Energie-Check:", exc)
        time.sleep(ENERGY_CHECK_SECONDS)


def measure_forever():
    """Misst immer wieder und legt die neueste Messung als data.hex in den Bucket."""
    while True:
        try:
            hexdata = antimatter_sensor_commands.measure()
            s3_client.put_object(S3_BUCKET, S3_OBJECT, hexdata)
            stats["uploads"] += 1
            stats["last"] = hexdata
            if not first_upload.is_set():
                print(f"[mission9] erste Messung in s3://{S3_BUCKET}/{S3_OBJECT}: {hexdata[:60]}...")
                first_upload.set()
        except Exception as exc:
            print("[mission9] Fehler bei Messung/Upload:", exc)
        time.sleep(ANTIMATTER_INTERVAL)


def _distance(a, b):
    return ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5


def _hold_position(here):
    """Punkt AETHERIUM_STANDOFF vor dem Aetherium Rock, auf der Seite, von der das Schiff kommt."""
    dx, dy = here["x"] - AETHERIUM_TARGET["x"], here["y"] - AETHERIUM_TARGET["y"]
    length = (dx ** 2 + dy ** 2) ** 0.5 or 1
    return {"x": AETHERIUM_TARGET["x"] + dx / length * AETHERIUM_STANDOFF,
            "y": AETHERIUM_TARGET["y"] + dy / length * AETHERIUM_STANDOFF}


def fly_and_stay():
    target = _hold_position(position())
    set_target(target)
    print(f"[mission9] Kurs auf {AETHERIUM_ROCK} ({AETHERIUM_TARGET['x']}/{AETHERIUM_TARGET['y']}), "
          f"Halte-Punkt {target['x']:.0f}/{target['y']:.0f}")
    arrived = False
    last_report = 0
    while True:
        try:
            here = position()
            gap = _distance(here, target)
            if not arrived and gap <= AETHERIUM_STAY_RADIUS:
                arrived = True
                print(f"[mission9] beim {AETHERIUM_ROCK} angekommen - bleibe hier, Analyzer Gamma laeuft")
            elif arrived and gap > AETHERIUM_STAY_RADIUS:
                print(f"[mission9] abgedriftet ({gap:.0f}), Kurs neu setzen")
                set_target(target)
            if time.time() - last_report >= REPORT_SECONDS:
                last_report = time.time()
                print(f"[mission9]  {here['x']:9.1f}/{here['y']:9.1f}   noch {gap:8.1f}   "
                      f"Messungen hochgeladen: {stats['uploads']}")
        except Exception as exc:
            print("[mission9] Fehler beim Positions-Check:", exc)
        time.sleep(RANGE_CHECK_SECONDS)


def run():
    start_s3_server()
    s3_client.ensure_bucket(S3_BUCKET)
    print(f"[mission9] S3 bereit: http://localhost:{S3_PORT}/{S3_BUCKET}/{S3_OBJECT}")

    threading.Thread(target=keep_power, daemon=True).start()
    threading.Thread(target=measure_forever, daemon=True).start()

    fly_and_stay()          # laeuft weiter, bis man mit Ctrl+C abbricht


if __name__ == "__main__":
    run()
