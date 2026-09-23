import secrets
import threading
import time

import requests
from flask import Flask, jsonify, redirect, request

from config import LASER_CLIENT_ID, LASER_CLIENT_SECRET, OAUTH_HOST, OAUTH_PORT

app = Flask(__name__)
codes = {}
token_issued = threading.Event()   # wird gesetzt, sobald das Schiff ein Token geholt hat


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

    if client_id != LASER_CLIENT_ID:
        return "Invalid client_id", 400
    if response_type != "code":
        return "Invalid response_type", 400
    if not redirect_uri:
        return "Missing redirect_uri", 400

    code = secrets.token_urlsafe(32)
    codes[code] = {"client_id": client_id, "redirect_uri": redirect_uri, "scope": scope}

    redirect_url = f"{redirect_uri}?code={code}"
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
    print("[oauth] Token Request:", data)

    if data.get("client_id") != LASER_CLIENT_ID:
        return jsonify({"error": "invalid_client"}), 401
    if data.get("client_secret") != LASER_CLIENT_SECRET:
        return jsonify({"error": "invalid_client", "error_description": "Wrong client secret"}), 401

    code = data.get("code")
    if code not in codes:
        return jsonify({"error": "invalid_grant"}), 400

    info = codes.pop(code)
    token_issued.set()
    print("[oauth] Token ausgestellt - Laser ist freigeschaltet.")
    return jsonify({
        "access_token": secrets.token_urlsafe(48),
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": info["scope"],
    })


def start_oauth_server():
    """Startet den OAuth-Server in einem Hintergrund-Thread. Das Schiff holt sich
    hier beim Laser-Login den Code und tauscht ihn gegen ein Token."""
    thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=OAUTH_PORT, use_reloader=False),
        daemon=True,
    )
    thread.start()

    for _ in range(20):
        try:
            if "OAuth Server" in requests.get(f"http://{OAUTH_HOST}:{OAUTH_PORT}/", timeout=1).text:
                print(f"[oauth] OAuth-Server laeuft auf {OAUTH_HOST}:{OAUTH_PORT}")
                return thread
        except requests.RequestException:
            time.sleep(0.5)
    raise RuntimeError(f"OAuth-Server nicht erreichbar auf {OAUTH_HOST}:{OAUTH_PORT} - Port belegt?")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=OAUTH_PORT)
