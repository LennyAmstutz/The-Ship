from config import command
from auth import SESSION


def activate():
    response = SESSION.post(command["laser_activate"])
    response.raise_for_status()
    return response.json()


def deactivate():
    response = SESSION.post(command["laser_deactivate"])
    response.raise_for_status()
    return response.json()


def set_angle(angle):
    response = SESSION.put(command["laser_angle"], json={"angle": angle})
    response.raise_for_status()
    return response.json()


def state():
    response = SESSION.get(command["laser_state"])
    response.raise_for_status()
    return response.json()