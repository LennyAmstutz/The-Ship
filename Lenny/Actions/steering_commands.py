import time

import requests
from config import command
from Actions.communication_commands import stations_in_reach


def set_target(target, timeout: float = 5.0):
    """Sende Ziel an den Steuerungs-Endpoint. Timeout ist in Sekunden.

    Bei HTTP-Fehlern/Netzwerkfehlern wird die requests-Exception weitergereicht.
    """
    response = requests.post(
        command["set_target"],
        json={"target": target},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def wait_until_in_reach(station_name, timeout=60, poll_interval=1.0, http_timeout=5.0):
    """Warte bis `station_name` in Reichweite ist.

    - timeout: maximale Wartezeit in Sekunden
    - poll_interval: Sekunden zwischen den Abfragen (kann Float sein)
    - http_timeout: Timeout für den HTTP-Request innerhalb von stations_in_reach

    Liefert True bei Erfolg, wirft TimeoutError wenn nicht gefunden.
    Exceptions aus requests werden intern behandelt (bei kurzzeitigen Netzwerkfehlern
    wird weiter versucht), längere Fehler führen zum Timeout.
    """
    start = time.monotonic()
    while True:
        elapsed = time.monotonic() - start
        if elapsed >= timeout:
            raise TimeoutError(f"{station_name} not in reach after {timeout}s")

        try:
            resp = stations_in_reach(timeout=http_timeout)
            stations = resp.get("stations", []) if isinstance(resp, dict) else []
        except requests.RequestException:
            # Netzwerkproblem — kurz warten und erneut prüfen bis timeout erreicht
            time.sleep(poll_interval)
            continue

        if station_name in stations:
            return True

        time.sleep(poll_interval)
