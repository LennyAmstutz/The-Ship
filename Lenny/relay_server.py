import queue
import threading

from flask import Flask, jsonify, request

from config import OWN_RELAY_HOST, OWN_RELAY_PORT

app = Flask(__name__)
inbox = queue.Queue()


@app.post("/relay")
def relay_in():
    data = request.get_json(force=True)
    print("[relay] Nachricht vom Partner erhalten:", data)
    inbox.put(data)
    return jsonify({"status": "ok"})


def start_relay_server():
    """Startet den Relay-Server in einem Hintergrund-Thread, damit die
    Mission-Schleife nebenher weiterlaufen kann."""
    thread = threading.Thread(
        target=lambda: app.run(
            host=OWN_RELAY_HOST, port=OWN_RELAY_PORT, use_reloader=False
        ),
        daemon=True,
    )
    thread.start()
    return thread
