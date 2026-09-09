import requests

from auth import get_access_token
from config import command

def _auth_headers():
    return {"Authorization": f"Bearer {get_access_token()}"}

def activate():
    response = requests.post(command["laser_activate"], headers=_auth_headers())
    response.raise_for_status()
    return response.json()

def deactivate():
    response = requests.post(command["laser_deactivate"], headers=_auth_headers())
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