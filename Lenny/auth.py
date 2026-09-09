import requests
from config import OAUTH

_token_cache = {"access_token": None}

def get_access_token():
    data = {
        "grant_type": OAUTH["grant_type"],
        "client_id": OAUTH["client_id"],
        "client_secret": OAUTH["client_secret"],
    }
    if OAUTH["scope"]:
        data["scope"] = OAUTH["scope"]

    response = requests.post(OAUTH["token_url"], data=data)
    response.raise_for_status()
    _token_cache["access_token"] = response.json()["access_token"]
    return _token_cache["access_token"]