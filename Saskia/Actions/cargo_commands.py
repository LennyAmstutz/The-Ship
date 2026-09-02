import requests
from config import command

def hold():
    response = requests.get(
        command["hold"])
    response.raise_for_status()
    return response.json()
