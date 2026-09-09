import time
import requests
from config import command, OAUTH

_token = None
_token_expires_at = 0

def _get_token():
    global _token, _token_expires_at
    if _token and time.time() < _token_expires_at - 5:
        return _token

    response = requests.post(
        OAUTH["token_url"],
        data={
            "grant_type": OAUTH["grant_type"],
            "client_id": OAUTH["client_id"],
            "client_secret": OAUTH["client_secret"],
            "scope": OAUTH.get("scope", ""),
        },
    )
    response.raise_for_status()
    payload = response.json()

    _token = payload["access_token"]
    _token_expires_at = time.time() + payload.get("expires_in", 3600)
    return _token

def mine(target=None):
    headers = {"Authorization": f"Bearer {_get_token()}"}
    payload = {"target": target} if target else {}
    response = requests.post(command["mine"], json=payload, headers=headers)
    response.raise_for_status()
    return response.json()