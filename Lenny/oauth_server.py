import secrets
import threading
import time

import requests
from flask import Flask, jsonify, redirect, request

from config import OAUTH_CLIENT_SECRETS, OAUTH_HOST, OAUTH_PORT

# OAuth2-Server (Authorization Code Flow) fuer die gefaehrlichen Geraete: Laser und Kernreaktor.
# Jedes Geraet bekommt beim configure_oauth sein eigenes client_secret; daran erkennt
# der Token-Endpunkt, welches Geraet sich gerade einloggt.

app = Flask(__name__)
codes = {}
# wird pro Geraet gesetzt, sobald es ein Token geholt hat
token_issued = {device: threading.Event() for device in OAUTH_CLIENT_SECRETS}
_started = False


@app.get("/")
def home():
    return jsonify({"status": "OAuth Server laeuft"})


@app.get("/authorize")
def authorize():
    client_id = request.args.get("client_id")
    redirect_uri = request.args.get("redirect_uri")
    response_type = request.args.get("response_type")
    scope = request.args.get("scope")
    state = request.args.get("state")
    print(f"[oauth] authorize client_id={client_id} redirect_uri={redirect_uri} scope={scope}")

    if not client_id:
        return "Missing client_id", 400
    if response_type != "code":
        return "Invalid response_type", 400
    if not redirect_uri:
        return "Missing redirect_uri", 400

    code = secrets.token_urlsafe(32)
    codes[code] = {"client_id": client_id, "redirect_uri": redirect_uri, "scope": scope}

    redirect_url = f"{redirect_uri}{'&' if '?' in redirect_uri else '?'}code={code}"
    if state:
        redirect_url += f"&state={state}"
    print("[oauth] Redirect zu:", redirect_url)
    return redirect(redirect_url)


@app.post("/token")
def token():
    data = dict(request.form or request.get_json(silent=True) or {})
    # Client-Daten koennen auch per HTTP Basic Auth kommen
    if request.authorization:
        data.setdefault("client_id", request.authorization.username)
        data.setdefault("client_secret", request.authorization.password)
    print("[oauth] Token Request:", {k: v for k, v in data.items() if k != "client_secret"})

    device = next((d for d, s in OAUTH_CLIENT_SECRETS.items() if s == data.get("client_secret")), None)
    if device is None:
        return jsonify({"error": "invalid_client", "error_description": "Wrong client secret"}), 401

    code = data.get("code")
    if code not in codes:
        return jsonify({"error": "invalid_grant"}), 400
    info = codes.pop(code)
    if data.get("client_id") and data["client_id"] != info["client_id"]:
        return jsonify({"error": "invalid_grant", "error_description": "Code gehoert zu einem anderen Client"}), 400

    token_issued[device].set()
    print(f"[oauth] Token ausgestellt fuer {device} (client_id={info['client_id']}) - freigeschaltet.")
    return jsonify({
        "access_token": secrets.token_urlsafe(48),
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": info["scope"],
    })


def start_oauth_server():
    """Startet den OAuth-Server in einem Hintergrund-Thread (nur einmal). Die Geraete holen sich
    hier beim Login den Code und tauschen ihn gegen ein Token."""
    global _started
    if _started:
        return
    thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=OAUTH_PORT, use_reloader=False),
        daemon=True,
    )
    thread.start()

    for _ in range(20):
        try:
            if "OAuth Server" in requests.get(f"http://{OAUTH_HOST}:{OAUTH_PORT}/", timeout=1).text:
                print(f"[oauth] OAuth-Server laeuft auf {OAUTH_HOST}:{OAUTH_PORT}")
                _started = True
                return
        except requests.RequestException:
            time.sleep(0.5)
    raise RuntimeError(f"OAuth-Server nicht erreichbar auf {OAUTH_HOST}:{OAUTH_PORT} - Port belegt?")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=OAUTH_PORT)
