"""Sensoren fuer Analyzer Delta: Sensor-Newton-Depth und Subspace-Tachyon-Scanner."""
import json
import re
from collections import Counter

import requests

from config import NEWTON_API_KEY, NEWTON_URL, TACHYON_URL

BUG_MARK = "---DETECTED BUG---"


# --- Sensor-Newton-Depth ------------------------------------------------------

def newton_depth():
    """GET /read mit X-API-KEY -> Hex-String."""
    response = requests.get(f"{NEWTON_URL}/read", headers={"X-API-KEY": NEWTON_API_KEY}, timeout=5)
    if not response.ok:
        raise RuntimeError(f"HTTP {response.status_code}, Body: {response.text[:500]!r}")
    text = response.text.strip()
    try:                     
        return json.loads(text)["data"]
    except (ValueError, KeyError, TypeError):
        return text


# --- Vektoruhren --------------------------------------------------------------

def parse_clock(line):
    """Liest die Vektoruhr hinter 'my time is' -> {prozess: zeit}.
    Versteht '0: 9', '0: 3, 1: 5' und '[3, 5]'."""
    part = line.split("my time is", 1)[1].replace(BUG_MARK, "")
    pairs = re.findall(r"(\d+)\s*:\s*(\d+)", part)
    if pairs:
        return {int(k): int(v) for k, v in pairs}
    numbers = re.findall(r"\d+", part)
    return {i: int(n) for i, n in enumerate(numbers)}


def happened_before(line_clock, bug_clock):
    """Ist die Zeile eine moegliche Ursache des Bugs?

    Regel (so wertet der Scanner aus, belegt durch seinen 'tip_for_next_try'):
    - die Zeile muss JEDE Komponente der Bug-Uhr enthalten. Zeilen mit fehlenden
      Komponenten (z.B. nur '0: 6') zaehlen NICHT, auch wenn die Zahlen kleiner sind
    - jede Komponente der Zeile ist <= der Komponente der Bug-Uhr
    - die Uhren sind nicht identisch
    """
    if not all(k in line_clock for k in bug_clock):
        return False
    if not all(v <= bug_clock.get(k, 0) for k, v in line_clock.items()):
        return False
    return line_clock != bug_clock


def find_causes(log):
    """Alle Log-Zeilen, die kausal VOR der Bug-Zeile liegen (Reihenfolge wie im Log)."""
    bug = next(line for line in log if BUG_MARK in line)
    bug_clock = parse_clock(bug)
    return [line for line in log
            if line is not bug and happened_before(parse_clock(line), bug_clock)]


# --- Subspace-Tachyon-Scanner -------------------------------------------------

def tachyon_status():
    response = requests.get(f"{TACHYON_URL}/status", timeout=5)
    response.raise_for_status()
    return response.json()


def _report_tip(sent, response_text):
    """Bei einer falschen Loesung liefert der Scanner die richtige als 'tip_for_next_try'.
    Wir vergleichen sie mit unserer Antwort und pruefen, ob unsere Regel den Tipp erklaert."""
    try:
        tip = json.loads(response_text).get("tip_for_next_try")
    except ValueError:
        return
    if not tip or "solution" not in tip:
        return
    right = Counter(tip["solution"])
    ours = Counter(sent)
    too_many = list((ours - right).elements())
    missing = list((right - ours).elements())
    print(f"[delta] Tipp des Scanners: {sum(right.values())} richtige Zeilen; "
          f"bei uns {len(too_many)} zu viel, {len(missing)} fehlen")
    for line in too_many[:10]:
        print("[delta]   zu viel:", line)
    for line in missing[:10]:
        print("[delta]   fehlt:  ", line)
    if tip.get("log"):
        same = Counter(find_causes(tip["log"])) == right
        print("[delta] Unsere Regel reproduziert den Tipp:", "JA" if same else "NEIN")


def tachyon_solve(log):
    causes = find_causes(log)
    response = requests.post(f"{TACHYON_URL}/solution", data=json.dumps(causes),
                             headers={"Content-Type": "application/json"}, timeout=5)
    print(f"[delta] /solution: HTTP {response.status_code}, gesendet {len(causes)} Zeilen")
    if not response.ok:
        _report_tip(causes, response.text)
        raise RuntimeError(f"Scanner lehnt die Loesung ab (HTTP {response.status_code}): "
                           f"{response.text[:150]!r}")
    return causes, response.json()


def tachyon_data():
    """Messung als Hex-String; wirft RuntimeError, solange der Scanner nicht online ist."""
    response = requests.get(f"{TACHYON_URL}/data", timeout=5)
    response.raise_for_status()
    result = response.json()
    if result.get("kind") != "success":
        raise RuntimeError(f"Scanner noch nicht bereit: {result}")
    return result["measurement"]