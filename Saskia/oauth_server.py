import secrets
import threading

from flask import Flask, jsonify, redirect, request

from config import LASER_CLIENT_ID, LASER_CLIENT_SECRET, OAUTH_PORT

app = Flask(__name__)
codes = {}


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
    data = request.form or request.get_json(silent=True) or {}
    print("[oauth] Token Request:", dict(data))

    if data.get("client_id") != LASER_CLIENT_ID:
        return jsonify({"error": "invalid_client"}), 401
    if data.get("client_secret") != LASER_CLIENT_SECRET:
        return jsonify({"error": "invalid_client", "error_description": "Wrong client secret"}), 401

    code = data.get("code")
    if code not in codes:
        return jsonify({"error": "invalid_grant"}), 400

    info = codes.pop(code)
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
    return thread


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=OAUTH_PORT)
