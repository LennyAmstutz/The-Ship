import requests
from Saskia.config import command

def stations_in_reach():
    response = requests.get(
        command["stations_in_reach"])
    response.raise_for_status()
    return response.json()

def buy(station, what, amount):
    response = requests.post(
        command["buy"],
        json={"station": station, "what": what, "amount": amount}
    )
    response.raise_for_status()
    return response.json()

def sell(station, what, amount):
    response = requests.post(
        command["sell"],
        json={"station": station, "what": what, "amount": amount}
    )
    response.raise_for_status()
    return response.json()