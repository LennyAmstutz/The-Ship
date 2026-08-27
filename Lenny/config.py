# --- Verbinden ---------------------------------------------------------
HOST = "192.168.101.50"
consume_host = HOST
consume_port = 2014

command = {
    "buy": f"http://{HOST}:2011/buy",
    "sell": f"http://{HOST}:2011/sell",
    "hold": f"http://{HOST}:2012/hold",
    "set_target" : f"http://{HOST}:2009/set_target",
    "stations_in_reach" : f"http://{HOST}:2011/stations_in_reach",
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

# WhatsUpp Mission
WHATSUPP_STATION = "G-Station 1-5"
WHATSUPP_COORDINATES = {"x": -19747, "y": -14282}
WHATSUPP_DURATION = 60  # 60 Sekunden
