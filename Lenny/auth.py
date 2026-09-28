import webbrowser

import requests

from config import AUTHORIZE_URL, OAUTH_CLIENT_SECRETS, TOKEN_URL, command
from oauth_server import start_oauth_server, token_issued

# OAuth2-Login fuer ein Geraet ("laser" oder "reactor"):
#   1. unseren OAuth-Server starten
#   2. dem Geraet per configure_oauth sagen, wo der Server ist und welches Secret es hat
#   3. /login des Geraets aufrufen - es holt sich bei uns Code und Token


def _configure_oauth(device):
    response = requests.post(command[f"{device}_configure_oauth"], json={
        "client_secret": OAUTH_CLIENT_SECRETS[device],
        "authorize_url": AUTHORIZE_URL,
        "token_url": TOKEN_URL,
    }, timeout=10)
    response.raise_for_status()
    return response.json()


def _auto_login(device):
    """Unser OAuth-Server winkt jeden Login durch, darum geht es auch ohne Browser:
    einfach /login aufrufen und den Weiterleitungen folgen."""
    token_issued[device].clear()
    try:
        response = requests.get(command[f"{device}_login"], timeout=15)
        print(f"[auth] {device}: Login-Antwort {response.status_code}: {response.text[:200]!r}")
    except requests.RequestException as exc:
        print(f"[auth] {device}: automatischer Login fehlgeschlagen:", exc)
    return token_issued[device].wait(timeout=5)


def login(device="laser", interactive=True):
    start_oauth_server()
    print(f"[auth] {device}: OAuth konfiguriert:", _configure_oauth(device))

    if _auto_login(device):
        print(f"[auth] {device}: Login erfolgreich.")
        return True
    if not interactive:
        print(f"[auth] {device}: WARNUNG - kein Token abgeholt.")
        return False

    url = command[f"{device}_login"]
    print(f"[auth] {device}: Bitte diese Adresse im Browser oeffnen:", url)
    webbrowser.open(url)
    input("[auth] Im Browser anmelden und danach hier ENTER druecken ...")
    if not token_issued[device].is_set():
        print(f"[auth] WARNUNG: {device} hat noch kein Token abgeholt - antwortet evtl. mit 401.")
    return token_issued[device].is_set()
