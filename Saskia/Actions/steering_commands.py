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

def position():
    response = requests.get(command["pos"])
    response.raise_for_status()
    data = response.json()
    if "x" in data:
        return data
    # Position steckt je nach Schiff in einem Unterobjekt, z.B. {"pos": {"x": .., "y": ..}}
    return next(value for value in data.values() if isinstance(value, dict) and "x" in value)

def wait_until_in_reach(station_name, timeout=60):
    waited = 0
    stations = stations_in_reach()["stations"]
    while station_name not in stations:
        if timeout is not None and waited >= timeout:
            raise TimeoutError(f"{station_name} not in reach after {timeout}s")
        time.sleep(1)
        waited += 1
        stations = stations_in_reach()["stations"]