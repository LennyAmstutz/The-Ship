import requests
from config import command


def activate():
    response = requests.post(command["laser_activate"], json={})
    response.raise_for_status()
    return response.json()


def deactivate():
    response = requests.post(command["laser_deactivate"], json={})
    response.raise_for_status()
    return response.json()


def set_angle(angle):
    response = requests.put(command["laser_angle"], json={"angle": angle})
    response.raise_for_status()
    return response.json()


def state():
    response = requests.get(command["laser_state"])
    response.raise_for_status()
    return response.json()
