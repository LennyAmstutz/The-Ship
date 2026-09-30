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
    "energy_nodes": [f"http://{HOST}:2032", f"http://{HOST}:2033"],
    "void_sensor": f"http://{HOST}:2037",
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

# Comm Module Aurora: eigenes Binaerprotokoll ueber TCP, wir sind der Client.
AURORA_HOST = HOST
AURORA_PORT = 2031

# --- Mission 6 (Schild) ----------------------------------------------------
# Energy-Management (Aktiv/Passiv): nur der aktive Node nimmt neue Limits an
SHIELD_LIMITS = {"sensor_void_energy": 1.0, "shield_generator": 1.0}
ENERGY_CHECK_SECONDS = 5

# Der Schildgenerator liest die Sensordaten aus dieser MongoDB (hardcodiert im Generator)
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
# Der Analyzer holt die Vakuumenergie-Daten per gRPC bei uns ab: grpc://192.168.101.51:2102
ANALYZER_LIMITS = {"sensor_void_energy": 1.0, "analyzer_alpha": 1.0}
GRPC_PORT = 2102
GRPC_WAIT_SECONDS = 10          # so lange wartet ein Aufruf hoechstens auf die erste Messung

URAN_STONE = "Uran Stone"
URAN_TARGET = {"x": -2100, "y": 3600}
URAN_STANDOFF = 50              # Abstand zum Stein (wie bei Arakrock nicht direkt drauf)
URAN_STAY_RADIUS = 30           # weiter weg vom Halte-Punkt -> Kurs neu setzen

# --- Mission 9 (Analyzer Gamma + S3) -------------------------------------
# Analyzer Gamma liest regelmaessig s3://analyzer-gamma/data.hex von http://192.168.101.51:2016.
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

REPORT_SECONDS = 10
