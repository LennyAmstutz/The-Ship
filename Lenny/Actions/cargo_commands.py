import requests
from config import command, STONE_RESOURCE

def hold():
    response = requests.get(
        command["hold"])
    response.raise_for_status()
    return response.json()

def stone_count():
    return hold()["hold"]["resources"].get(STONE_RESOURCE, 0)

def free_space():
    return hold()["hold"]["hold_free"]

def hold_size():
    return hold()["hold"]["hold_size"]
