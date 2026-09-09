import requests
from config import command
from auth import get_access_token

def _headers():
    return {"Authorization": f"Bearer {get_access_token()}"}

def activate():
    response = requests.post(command["laser_activate"], headers=_headers())
    response.raise_for_status()
    return response.json()

def deactivate():
    response = requests.post(command["laser_deactivate"], headers=_headers())
    response.raise_for_status()
    return response.json()

def set_angle(angle):
    response = requests.put(command["laser_angle"], json={"angle": angle}, headers=_headers())
    response.raise_for_status()
    return response.json()

def state():
    response = requests.get(command["laser_state"], headers=_headers())
    response.raise_for_status()
    return response.json()