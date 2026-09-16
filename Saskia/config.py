# --- Verbinden ---------------------------------------------------------
HOST = "192.168.101.51"
consume_host = HOST
PARTNER_HOST = "192.168.101.50"
consume_port = 2014
PARTNER_RELAY_PORT = 5001

command = {
    "buy": f"http://{HOST}:2011/buy",
    "sell": f"http://{HOST}:2011/sell",
    "hold": f"http://{HOST}:2012/hold",
    "set_target" : f"http://{HOST}:2009/set_target",
    "pos" :  f"http://{HOST}:2011/pos",
    "stations_in_reach" : f"http://{HOST}:2011/stations_in_reach",
    "comm_elyse_ws": f"ws://{HOST}:2026/api",
    "partner_relay": f"http://{PARTNER_HOST}:{PARTNER_RELAY_PORT}/relay",
}

# --- Mission 1 ---------------------------------------------------------
RESOURCE = "IRON"

BUY_STATION = "Azura Station"
SELL_STATION = "Core Station"

# --- Mission 2 ---------------------------------------------------------
COMM_MODULE_ELYSE_PORT = 2026

ELYSE_STATION = "Elyse Terminal"
SHANGRIS_STATION = "Shangris Station"

ELYSE_TARGET = {"x": -70565, "y": 72811}
SHANGRIS_TARGET = {"x": 4446, "y": 4340}

MISSION2_MAX_GAP = 3
MISSION2_HOLD_SECONDS = 20

OWN_RELAY_HOST = "0.0.0.0"
OWN_RELAY_PORT = 5001

# --- Mission 3 ---------------------------------------------------------
SCAN_QUEUE = "scanner"
RABBITMQ_USER = "tags"
RABBITMQ_PASS = "DEIN_ECHTES_PASSWORT"

WHATSUPP_STATION = "G-Station 1-5"
HOLD_SECONDS = 60
HINT = {"x": -19747, "y": -14282}