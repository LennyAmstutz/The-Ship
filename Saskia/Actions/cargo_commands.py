import requests
from Saskia.config import command

def hold():
    response = requests.get(
        command["hold"])
    response.raise_for_status()
    return response.json()
