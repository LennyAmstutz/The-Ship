# --- Verbinden ---------------------------------------------------------
HOST = "192.168.101.50"
consume_host = HOST
consume_port = 2014

command = {
    "buy": f"http://{HOST}:2011/buy",
    "sell": f"http://{HOST}:2011/sell",
    "hold": f"http://{HOST}:2012/hold",
    "set_target": f"http://{HOST}:2009/set_target",
    "stations_in_reach": f"http://{HOST}:2011/stations_in_reach",
    "laser_activate": f"http://{HOST}:2018/activate",
    "laser_deactivate": f"http://{HOST}:2018/deactivate",
    "laser_angle": f"http://{HOST}:2018/angle",
    "laser_state": f"http://{HOST}:2018/state",
}

# --- Mission 1 ---------------------------------------------------------
RESOURCE = "IRON"

BUY_STATION = "Azura Station"
SELL_STATION = "Core Station"

# --- Mission 2 ---------------------------------------------------------

# --- Mission 3 ---------------------------------------------------------
SCAN_QUEUE = "scanner"
RABBITMQ_USER = "tags"
RABBITMQ_PASS = "[administrator]"

WHATSUPP_STATION = "G-Station 1-5"
HOLD_SECONDS = 60
HINT = {"x": -19747, "y": -14282}

# --- Mission 4 ---------------------------------------------------------
OAUTH = {
    "token_url": "http://192.168.101.50:8080/realms/ship/protocol/openid-connect/token",
    "client_id": "laser-client",
    "client_secret": "gsX3ggGNQTEpjraMHlFgN9svWPj1FHekOHGcSH082B1YIq5ifWbLatCKwj0cFMJG5ccnY8UfK7CfVEJz9CdbOv",
    "grant_type": "client_credentials",
    "scope": "",
}

MINE_TARGET = {"x": -18236, "y": -11783}
STONE_RESOURCE = "STONE"
STONE_AMOUNT = 12

VESTA_STATION = "Vesta Station"
VESTA_TARGET = {"x": 7000, "y": 7000}
