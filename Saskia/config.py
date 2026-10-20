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
AURORA_STATION = "Aurora Station"
AURORA_TARGET = {"x": -6000, "y": 7000}

AURORA_HOST = HOST
AURORA_PORT = 2031

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


# --- Mission 8: Analyzer Delta --------------------------------------------
 
DELTA_LIMITS = {
    "sensor_newton_depth": 1.0,
    "subspace_tachyon_scanner": 1.0,
    "analyzer_delta": 1.0,
}
 
DELTA_PORT = 2105
DELTA_WAIT_SECONDS = 10
 
NEWTON_URL = f"http://{HOST}:2044"
NEWTON_API_KEY = "foobar"            # Key aus der Doku des Sensors - falls anders, hier anpassen
TACHYON_URL = f"http://{HOST}:2041"
 
MAGNON_ROCK = "Magnon Rock"
MAGNON_TARGET = {"x": 37062, "y": 17964}
MAGNON_STANDOFF = 50
MAGNON_STAY_RADIUS = 30

 
# --- Mission 9 (Analyzer Gamma + S3) -------------------------------------
S3_HOST = HOST
S3_PORT = 2016
S3_BUCKET = "analyzer-gamma"
S3_OBJECT = "data.hex"
S3_ACCESS_KEY = "theship"
S3_SECRET_KEY = "theship1234"
S3_REGION = "us-east-1"
S3_CHECK_SIGNATURE = True       

ANTIMATTER_AXES = ("x", "y", "z")
ANTIMATTER_TIMEOUT = 120       
ANTIMATTER_INTERVAL = 2         

GAMMA_LIMITS = {"sensor_antimatter": 1.0, "analyzer_gamma": 1.0,
                "laser": 0.0, "nuclear_reactor": 0.0, "analyzer_beta": 0.0,
                "scanner": 0.0, "sensor_void_energy": 0.0, "analyzer_alpha": 0.0}

AETHERIUM_ROCK = "Aetherium Rock"
AETHERIUM_TARGET = {"x": 30957, "y": -28933}
AETHERIUM_STANDOFF = 50         
AETHERIUM_STAY_RADIUS = 30     

REPORT_SECONDS = 10
