import time

import requests
from config import command, SENSOR_POLL_SECONDS, SENSOR_TIMEOUT

# Vakuumenergie-Sensor: Messung ausloesen, Ergebnis abholen, Ergebnis wieder loeschen.
# Wer eine Messung ausloest, ist ihr Besitzer (Resource Owner) und muss sie auch loeschen -
# sonst laeuft der Speicher des Sensors voll.


def trigger(request_id):
    response = requests.post(f"{command['void_sensor']}/trigger_measurement",
                             json={"request_id": request_id}, timeout=5)
    response.raise_for_status()


def measurement(request_id):
    response = requests.get(f"{command['void_sensor']}/measurements/{request_id}", timeout=5)
    response.raise_for_status()
    return response.json()


def delete(request_id):
    response = requests.delete(f"{command['void_sensor']}/measurements/{request_id}", timeout=5)
    response.raise_for_status()


def measure(request_id):
    """Loest eine Messung aus, wartet auf das Ergebnis (Hex-String) und loescht die Messung danach."""
    trigger(request_id)
    try:
        waited = 0
        while True:
            result = measurement(request_id)
            if result.get("state") == "measured":
                return result["result"]
            if waited >= SENSOR_TIMEOUT:
                raise TimeoutError(f"Messung {request_id} nach {SENSOR_TIMEOUT}s noch nicht fertig: {result}")
            time.sleep(SENSOR_POLL_SECONDS)
            waited += SENSOR_POLL_SECONDS
    finally:
        try:
            delete(request_id)
        except requests.RequestException as exc:
            print(f"[sensor] Messung {request_id} konnte nicht geloescht werden: {exc}")
