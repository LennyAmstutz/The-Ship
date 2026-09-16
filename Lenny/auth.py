import re

import requests

from config import AUTHORIZE_URL, LASER_CLIENT_SECRET, TECH_PASSWORD, TECH_USERNAME, TOKEN_URL, command

SESSION = requests.Session()


def _configure_oauth():
    response = SESSION.post(command["laser_configure_oauth"], json={
        "client_secret": LASER_CLIENT_SECRET,
        "authorize_url": AUTHORIZE_URL,
        "token_url": TOKEN_URL,
    })
    response.raise_for_status()
    return response.json()


def login():
    _configure_oauth()

    login_page = SESSION.get(command["laser_login"])
    login_page.raise_for_status()

    match = re.search(r'action="([^"]+)"', login_page.text)
    if not match:
        raise RuntimeError("Login-Formular nicht gefunden - Keycloak-Loginseite hat sich vermutlich geaendert.")
    form_action = match.group(1).replace("&amp;", "&")

    response = SESSION.post(form_action, data={
        "username": TECH_USERNAME,
        "password": TECH_PASSWORD,
    })
    response.raise_for_status()
    print(f"[auth] Login-Antwort {response.status_code}: {response.text[:200]!r}")
    return response