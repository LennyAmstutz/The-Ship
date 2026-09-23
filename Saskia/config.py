# --- Verbinden ---------------------------------------------------------
HOST = "192.168.101.51"
consume_host = HOST
consume_port = 2014

PARTNER_HOST = "192.168.101.50"
PARTNER_RELAY_PORT = 5001


command = {
    "buy": f"http://{HOST}:2011/buy",
    "sell": f"http://{HOST}:2011/sell",
    "hold": f"http://{HOST}:2012/hold",
    "pos": f"http://{HOST}:2011/pos",
    "set_target": f"http://{HOST}:2009/set_target",
    "stations_in_reach": f"http://{HOST}:2011/stations_in_reach",
    "laser_configure_oauth": f"http://{HOST}:2018/configure_oauth",
    "laser_login": f"http://{HOST}:2018/login",
    "laser_activate": f"http://{HOST}:2018/activate",
    "laser_deactivate": f"http://{HOST}:2018/deactivate",
    "laser_angle": f"http://{HOST}:2018/angle",
    "laser_state": f"http://{HOST}:2018/state",
    "comm_shangris_ws": f"ws://{HOST}:2025/ws",
    "partner_relay": f"http://{PARTNER_HOST}:{PARTNER_RELAY_PORT}/relay",
}

# --- Mission 1 ---------------------------------------------------------
RESOURCE = "IRON"

BUY_STATION = "Azura Station"
SELL_STATION = "Core Station"

# --- Mission 2 ---------------------------------------------------------
ELYSE_STATION = "Elyse Terminal"
SHANGRIS_STATION = "Shangris Station"

ELYSE_TARGET = {"x": -70565, "y": 72811}
SHANGRIS_TARGET = {"x": 4446, "y": 4340}

COMM_KEY = "data"
SEND_PAUSE = 1.0
RANGE_CHECK_SECONDS = 2

OWN_RELAY_HOST = "0.0.0.0"
OWN_RELAY_PORT = 5002

# --- Mission 3 ---------------------------------------------------------
SCAN_QUEUE = "scanner"
RABBITMQ_USER = "tags"
RABBITMQ_PASS = "DEIN_ECHTES_PASSWORT"

WHATSUPP_STATION = "G-Station 1-5"
HOLD_SECONDS = 60
HINT = {"x": -19747, "y": -14282}

# --- Mission 4 -----------------------------------------------------------
# Der OAuth-Server laeuft zusammen mit diesem Code auf der Schiff-VM.
# Port 2015 ist dort vom RabbitMQ-Dashboard belegt, darum 5015.
OAUTH_HOST = HOST
OAUTH_PORT = 5015
AUTHORIZE_URL = f"http://{OAUTH_HOST}:{OAUTH_PORT}/authorize"
TOKEN_URL = f"http://{OAUTH_HOST}:{OAUTH_PORT}/token"
LASER_CLIENT_ID = "laser"
LASER_CLIENT_SECRET = "meinLaserSecret123"

MINE_TARGET = {"x": -18236, "y": -11783}
STONE_RESOURCE = "STONE"

VESTA_STATION = "Vesta Station"
VESTA_TARGET = {"x": 7000, "y": 7000}

MINING_STANDOFF = 120
ARRIVAL_RADIUS = 15
ANGLE_STEP = 5
LASER_POLL_SECONDS = 2

# --- Mission 5 (Kommunikation Reloaded) ----------------------------------
# Aurora Station (Saskia) <-> Vesta Station (Lenny)
AURORA_STATION = "Aurora Station"
AURORA_TARGET = {"x": -6000, "y": 7000}

# Das Comm Module Aurora verbindet sich selbst mit diesem MQTT-Server (siehe k8s/mosquitto.yaml).
# Falls in der Doku vom Modul ein anderer Port steht: hier und in k8s/mosquitto.yaml (nodePort) anpassen.
MQTT_HOST = HOST
MQTT_PORT = 2036
AURORA_RX_TOPIC = f"shipcomm/{AURORA_STATION}/rx"   # hier publisht Aurora, was sie versenden will
AURORA_TX_TOPIC = f"shipcomm/{AURORA_STATION}/tx"   # hier empfaengt Aurora Nachrichten
