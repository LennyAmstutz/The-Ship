import webbrowser

import requests

from config import AUTHORIZE_URL, LASER_CLIENT_SECRET, TOKEN_URL, command
from oauth_server import start_oauth_server, token_issued


def _configure_oauth():
    response = requests.post(command["laser_configure_oauth"], json={
        "client_secret": LASER_CLIENT_SECRET,
        "authorize_url": AUTHORIZE_URL,
        "token_url": TOKEN_URL,
    })
    response.raise_for_status()
    return response.json()


def _auto_login():
    """Unser OAuth-Server winkt jeden Login durch, darum geht es auch ohne Browser:
    einfach /login aufrufen und den Weiterleitungen folgen."""
    try:
        response = requests.get(command["laser_login"], timeout=15)
        print(f"[auth] Login-Antwort {response.status_code}: {response.text[:200]!r}")
    except requests.RequestException as exc:
        print("[auth] Automatischer Login fehlgeschlagen:", exc)
    return token_issued.wait(timeout=5)


def login():
    start_oauth_server()
    print("[auth] OAuth:", _configure_oauth())
    print(f"[auth] OAuth-Server: {AUTHORIZE_URL} / {TOKEN_URL}")

    if _auto_login():
        print("[auth] Laser-Login erfolgreich.")
        return

    url = command["laser_login"]
    print("[auth] Bitte diese Adresse im Browser oeffnen:", url)
    webbrowser.open(url)
    input("[auth] Im Browser anmelden und danach hier ENTER druecken ...")
    if not token_issued.is_set():
        print("[auth] WARNUNG: Das Schiff hat noch kein Token abgeholt - der Laser antwortet evtl. mit 401.")
