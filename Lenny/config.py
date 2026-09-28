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
    "pos": f"http://{HOST}:2011/pos",
    "set_target": f"http://{HOST}:2009/set_target",
    "stations_in_reach": f"http://{HOST}:2011/stations_in_reach",
    "laser_configure_oauth": f"http://{HOST}:2018/configure_oauth",
    "laser_login": f"http://{HOST}:2018/login",
    "laser_activate": f"http://{HOST}:2018/activate",
    "laser_deactivate": f"http://{HOST}:2018/deactivate",
    "laser_angle": f"http://{HOST}:2018/angle",
    "laser_state": f"http://{HOST}:2018/state",
    "comm_elyse_ws": f"ws://{HOST}:2026/api",
    "partner_relay": f"http://{PARTNER_HOST}:{PARTNER_RELAY_PORT}/relay",
    "energy_nodes": [f"http://{HOST}:2032", f"http://{HOST}:2033"],
    "void_sensor": f"http://{HOST}:2037",
    "reactor_configure_oauth": f"http://{HOST}:2039/configure_oauth",
    "reactor_login": f"http://{HOST}:2039/login",
    "reactor_seconds_left": f"http://{HOST}:2039/seconds_left",
    "antimatter_sensor": f"http://{HOST}:2043",
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

COMM_KEY = "msg"
SEND_PAUSE = 1.0
RANGE_CHECK_SECONDS = 2

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
OAUTH_HOST = HOST
OAUTH_PORT = 5015
AUTHORIZE_URL = f"http://{OAUTH_HOST}:{OAUTH_PORT}/authorize"
TOKEN_URL = f"http://{OAUTH_HOST}:{OAUTH_PORT}/token"
LASER_CLIENT_ID = "laser"
LASER_CLIENT_SECRET = "meinLaserSecret123"
REACTOR_CLIENT_SECRET = "meinReaktorSecret123"
# Geraet -> client_secret. Unser OAuth-Server erkennt am Secret, welches Geraet sich einloggt.
OAUTH_CLIENT_SECRETS = {"laser": LASER_CLIENT_SECRET, "reactor": REACTOR_CLIENT_SECRET}

MINE_TARGET = {"x": -18236, "y": -11783}
STONE_RESOURCE = "STONE"

VESTA_STATION = "Vesta Station"
VESTA_TARGET = {"x": 7000, "y": 7000}

MINING_STANDOFF = 120
ARRIVAL_RADIUS = 15
ANGLE_STEP = 5
LASER_POLL_SECONDS = 2

# --- Mission 5 (Kommunikation Reloaded) ----------------------------------
AURORA_STATION = "Aurora Station"
AURORA_TARGET = {"x": -6000, "y": 7000}

MQTT_HOST = HOST
MQTT_PORT = 2036
VESTA_RX_TOPIC = f"shipcomm/{VESTA_STATION}/rx"
VESTA_TX_TOPIC = f"shipcomm/{VESTA_STATION}/tx"

# --- Mission 6 (Schild) ----------------------------------------------------
SHIELD_LIMITS = {"sensor_void_energy": 1.0, "shield_generator": 1.0}
ENERGY_CHECK_SECONDS = 5

MONGO_HOST = HOST
MONGO_PORT = 2021
MONGO_USER = "theship"
MONGO_PASSWORD = "theship1234"
MONGO_DB = "theshipdb"
VACUUM_COLLECTION = "vacuum-energy"

SENSOR_POLL_SECONDS = 0.5
SENSOR_TIMEOUT = 30
SENSOR_INTERVAL = 2

RELIEF_STATION = "Relief Station"
RELIEF_TARGET = {"x": 150000, "y": 150000}

# --- Mission 7 (Analyzer Alpha) ----------------------------------------------
ANALYZER_LIMITS = {"sensor_void_energy": 1.0, "analyzer_alpha": 1.0}
GRPC_PORT = 2102
GRPC_WAIT_SECONDS = 10

URAN_STONE = "Uran Stone"
URAN_TARGET = {"x": -2100, "y": 3600}
URAN_STANDOFF = 50
URAN_STAY_RADIUS = 30

# --- Mission 8 (Analyzer Beta + Kernreaktor) ------------------------------
# Analyzer Beta braucht viel Strom -> Kernreaktor (OAuth-Login, verbrennt Uran aus dem Laderaum).
# Das Uran wird mit dem Laser am Uran Stone (URAN_TARGET) abgebaut.
# Reaktor und Analyzer laufen nur beim Gold Stone, damit unterwegs kein Uran verbrennt.
MINING_LIMITS = {"laser": 1.0, "nuclear_reactor": 0.0, "analyzer_beta": 0.0,
                 "scanner": 0.0, "sensor_void_energy": 0.0, "analyzer_alpha": 0.0}
ANALYSIS_LIMITS = {"laser": 0.0, "nuclear_reactor": 1.0, "analyzer_beta": 1.0,
                   "scanner": 0.0, "sensor_void_energy": 0.0, "analyzer_alpha": 0.0}

URAN_RESOURCE = "URAN"          # zaehlt alles im Laderaum, dessen Name URAN enthaelt (URAN, URANIUM, ...)
GOLD_STONE = "Gold Stone"
GOLD_TARGET = {"x": -10000, "y": 333}
GOLD_STANDOFF = 50              # Abstand zum Gold Stone
GOLD_STAY_RADIUS = 30           # weiter weg vom Halte-Punkt -> Kurs neu setzen

CORE_STATION = "Core Station"   # kauft fast alles - hier wird Fremdes aus dem Laderaum verkauft
CORE_TARGET = {"x": 0, "y": 0}

REPORT_SECONDS = 10
REACTOR_STALL_SECONDS = 10      # so lange darf der Reaktor trotz Uran stehen, bevor neu eingeloggt wird

# --- Mission 9 (Analyzer Gamma + S3) -------------------------------------
# Analyzer Gamma liest regelmaessig s3://analyzer-gamma/data.hex von http://192.168.101.50:2016.
# Die Konfiguration im Analyzer ist hardcodiert - unser S3-Server muss genau so heissen.
S3_HOST = HOST
S3_PORT = 2016
S3_BUCKET = "analyzer-gamma"
S3_OBJECT = "data.hex"
S3_ACCESS_KEY = "theship"
S3_SECRET_KEY = "theship1234"
S3_REGION = "us-east-1"
S3_CHECK_SIGNATURE = True       # False: Server nimmt jede Anfrage mit dem richtigen access key an

# Antimateriesensor: x, y und z muessen GLEICHZEITIG messen, einer davon liefert das Resultat
ANTIMATTER_AXES = ("x", "y", "z")
ANTIMATTER_TIMEOUT = 120        # so lange darf eine Messung (alle 3 Achsen) dauern
ANTIMATTER_INTERVAL = 2         # Pause zwischen zwei Messungen

GAMMA_LIMITS = {"sensor_antimatter": 1.0, "analyzer_gamma": 1.0,
                "laser": 0.0, "nuclear_reactor": 0.0, "analyzer_beta": 0.0,
                "scanner": 0.0, "sensor_void_energy": 0.0, "analyzer_alpha": 0.0}

AETHERIUM_ROCK = "Aetherium Rock"
AETHERIUM_TARGET = {"x": 30957, "y": -28933}
AETHERIUM_STANDOFF = 50         # Abstand zum Aetherium Rock
AETHERIUM_STAY_RADIUS = 30      # weiter weg vom Halte-Punkt -> Kurs neu setzen
