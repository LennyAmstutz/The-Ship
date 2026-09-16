# --- Verbinden ---------------------------------------------------------
HOST = "192.168.101.50"
consume_host = HOST
consume_port = 2014
PARTNER_HOST = "192.168.101.51"
PARTNER_RELAY_PORT = 5002

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
RABBITMQ_PASS = "[administrator]"

WHATSUPP_STATION = "G-Station 1-5"
HOLD_SECONDS = 60
HINT = {"x": -19747, "y": -14282}

# --- Mission 4 -----------------------------------------------------------
KEYCLOAK_BASE = "http://192.168.101.50:8080/realms/ship/protocol/openid-connect"
AUTHORIZE_URL = f"{KEYCLOAK_BASE}/auth"
TOKEN_URL = f"{KEYCLOAK_BASE}/token"
LASER_CLIENT_SECRET = "gsX3ggGNQTEpjraMHlFgN9svWPj1FHekOHGcSH082B1YIq5ifWbLatCKwj0cFMJG5ccnY8UfK7CfVEJz9CdbOv"

TECH_USERNAME = "TODO_USERNAME"
TECH_PASSWORD = "TODO_PASSWORD"

MINE_TARGET = {"x": -18236, "y": -11783}
STONE_RESOURCE = "STONE"
STONE_AMOUNT = 12

VESTA_STATION = "Vesta Station"
VESTA_TARGET = {"x": 7000, "y": 7000}

MINING_STANDOFF = 300
ARRIVAL_RADIUS = 20
ANGLE_STEP = 6
LASER_BURN_SECONDS = 8
