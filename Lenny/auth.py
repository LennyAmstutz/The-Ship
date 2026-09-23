import webbrowser

import requests

from config import AUTHORIZE_URL, LASER_CLIENT_SECRET, TOKEN_URL, command
from oauth_server import start_oauth_server


def _configure_oauth():
    response = requests.post(command["laser_configure_oauth"], json={
        "client_secret": LASER_CLIENT_SECRET,
        "authorize_url": AUTHORIZE_URL,
        "token_url": TOKEN_URL,
    })
    response.raise_for_status()
    return response.json()


def login():
    start_oauth_server()
    print("[auth] OAuth:", _configure_oauth())
    print(f"[auth] OAuth-Server: {AUTHORIZE_URL} / {TOKEN_URL}")

    url = command["laser_login"]
    print("[auth] OAuth Login wird geoeffnet:", url)
    webbrowser.open(url)
    input("[auth] Im Browser anmelden und danach hier ENTER druecken ...")
