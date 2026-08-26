import time

import requests
from config import command
from Actions.communication_commands import stations_in_reach


def set_target(target):
    response = requests.post(
        command["set_target"],
        json={"target": target}
    )
    response.raise_for_status()
    return response.json()

def wait_until_in_reach(station_name, timeout=60):
    waited = 0
    stations = stations_in_reach()["stations"]
    while station_name not in stations:
        if waited >= timeout:
            raise TimeoutError(f"{station_name} not in reach after {timeout}s")
        time.sleep(1)
        waited += 1
        stations = stations_in_reach()["stations"]
