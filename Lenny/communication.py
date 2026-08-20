import requests
import cargo
url = "http://10.255.255.254:2011/"


def buy(station, what, amount):
    payload = {
        "station": station,
        "what": what,
        "amount": amount
    }
    while cargo.get_free_hold()>5:
        cargo.bewege_nach_hinten_wenn_voll()
        requests.post(url + "buy", json=payload)


def sell(station, what, amount):
    payload = {
        "station": station,
        "what": what,
        "amount": amount
    }
    return requests.post(url + "sell", json=payload)


def buy_item(station, what):
    payload = {
        "station": station,
        "what": what,
    }
    return requests.post(url + "buy_item", json=payload)


def get_near_station():
    return requests.get(url + "stations_in_reach")

def is_ship_at_station(station):
    stations_json = get_near_station().json()["stations"]
    return stations_json and list(stations_json.keys())[0] == station