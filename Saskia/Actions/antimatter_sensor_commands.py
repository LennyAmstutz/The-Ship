from concurrent.futures import ThreadPoolExecutor

import requests
from config import ANTIMATTER_AXES, ANTIMATTER_TIMEOUT, command

# Antimateriesensor: misst nur, wenn x, y und z GLEICHZEITIG laufen (wie "curl ... &" + "wait").
#   POST /x/measure, POST /y/measure, POST /z/measure
# Alle drei antworten {"kind": "success"}, EINER davon zusaetzlich mit "measurement": "<hex>".
# Nacheinander aufgerufen wuerde jeder Aufruf auf die anderen beiden warten -> darum 3 Threads.

_pool = ThreadPoolExecutor(max_workers=len(ANTIMATTER_AXES), thread_name_prefix="antimatter")


def _measure_axis(axis):
    response = requests.post(f"{command['antimatter_sensor']}/{axis}/measure", timeout=ANTIMATTER_TIMEOUT)
    response.raise_for_status()
    return axis, response.json()


def measure():
    """Startet die 3 Achsen gleichzeitig, wartet auf alle ("wait") und gibt den Hex-String zurueck."""
    futures = [_pool.submit(_measure_axis, axis) for axis in ANTIMATTER_AXES]
    results = dict(future.result() for future in futures)       # wirft den Fehler einer Achse weiter

    failed = {axis: result for axis, result in results.items() if result.get("kind") != "success"}
    if failed:
        raise RuntimeError(f"Antimateriesensor meldet Fehler: {failed}")
    for result in results.values():
        if result.get("measurement"):
            return result["measurement"]
    raise RuntimeError(f"Antimateriesensor hat keine Messung geliefert: {results}")
