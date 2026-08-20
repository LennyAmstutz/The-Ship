import requests
import time
import config as cfg

# --- API -------------------------------------------------------------

def hold():
    return requests.get(f"{cfg.HOLD}/hold", timeout=cfg.TIMEOUT).json()["hold"]


def stations():
    return requests.get(f"{cfg.NAV}/stations_in_reach", timeout=cfg.TIMEOUT).json()["stations"]


def set_target(target):
    return requests.post(f"{cfg.STEER}/set_target", json={"target": target},
                         timeout=cfg.TIMEOUT).json()


# --- Fliegen ---------------------------------------------------------

def fly_to(station):
    print(f"-> {station}")
    set_target(station)
    while station not in stations():
        time.sleep(1)
    time.sleep(0.5)


# --- Handeln ---------------------------------------------------------

def price(station):
    return stations()[station]["resources"][cfg.RESOURCE]["buy_price"]


def travel_and_buy():
    fly_to(cfg.BUY_STATION)

    h = hold()
    p = price(cfg.BUY_STATION)
    amount = int(min(h["credits"] // p, h["hold_free"]))

    if amount <= 0:
        print("   nichts zu kaufen")
        return 0

    requests.post(f"{cfg.NAV}/buy", timeout=cfg.TIMEOUT,
                  json={"station": cfg.BUY_STATION,
                        "what": cfg.RESOURCE,
                        "amount": amount})
    print(f"   gekauft: {amount}")
    return amount


def travel_and_sell():
    fly_to(cfg.SELL_STATION)

    amount = hold()["resources"].get(cfg.RESOURCE, 0)
    if amount <= 0:
        print("   nichts zu verkaufen")
        return 0

    for _ in range(amount // cfg.SELL_CHUNK + 1):
        requests.post(f"{cfg.NAV}/sell", timeout=cfg.TIMEOUT,
                      json={"station": cfg.SELL_STATION,
                            "what": cfg.RESOURCE,
                            "amount": cfg.SELL_CHUNK})
        time.sleep(0.2)

    print(f"   verkauft: {amount}")
    print(f"   Credits: {hold()['credits']}")
    return amount


def travel_to_vesta():
    print("-> Vesta Station")
    set_target({"x": cfg.VESTA_X, "y": cfg.VESTA_Y})

    while True:
        p = requests.get(f"{cfg.NAV}/pos", timeout=cfg.TIMEOUT).json()["pos"]
        if abs(p["x"] - cfg.VESTA_X) < 100 and abs(p["y"] - cfg.VESTA_Y) < 100:
            break
        time.sleep(1)

    print("   angekommen")