"""Sensoren fuer Analyzer Delta: Sensor-Newton-Depth und Subspace-Tachyon-Scanner."""
import json
import re

import requests

from config import NEWTON_API_KEY, NEWTON_URL, TACHYON_URL

BUG_MARK = "---DETECTED BUG---"


# --- Sensor-Newton-Depth ------------------------------------------------------

def newton_depth():
    """GET /read mit X-API-KEY -> Hex-String."""
    response = requests.get(f"{NEWTON_URL}/read", headers={"X-API-KEY": NEWTON_API_KEY}, timeout=5)
    response.raise_for_status()
    return response.text.strip()


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


def happened_before(a, b):
    """a -> b : in jeder Komponente a <= b und mindestens eine echt kleiner."""
    keys = set(a) | set(b)
    return a != b and all(a.get(k, 0) <= b.get(k, 0) for k in keys)


def find_causes(log):
    """Alle Log-Zeilen, die kausal VOR der Bug-Zeile liegen (nebenlaeufige/spaetere scheiden aus)."""
    bug = next(line for line in log if BUG_MARK in line)
    bug_clock = parse_clock(bug)
    return [line for line in log
            if line is not bug and happened_before(parse_clock(line), bug_clock)]


# --- Subspace-Tachyon-Scanner -------------------------------------------------

def tachyon_status():
    response = requests.get(f"{TACHYON_URL}/status", timeout=5)
    response.raise_for_status()
    return response.json()


def tachyon_solve(log):
    causes = find_causes(log)
    response = requests.post(f"{TACHYON_URL}/solution", data=json.dumps(causes),
                             headers={"Content-Type": "application/json"}, timeout=5)
    # Die Antwort des Scanners immer anzeigen - bei einem 400 steht dort meist der Grund
    print(f"[delta] /solution: HTTP {response.status_code}, Antwort: {response.text!r}")
    print(f"[delta] gesendet wurden {len(causes)} Zeilen: {json.dumps(causes)}")
    if not response.ok:
        raise RuntimeError(f"Scanner lehnt die Loesung ab (HTTP {response.status_code})")
    return causes, response.json()


def tachyon_data():
    """Messung als Hex-String; wirft RuntimeError, solange der Scanner nicht online ist."""
    response = requests.get(f"{TACHYON_URL}/data", timeout=5)
    response.raise_for_status()
    result = response.json()
    if result.get("kind") != "success":
        raise RuntimeError(f"Scanner noch nicht bereit: {result}")
    return result["measurement"]