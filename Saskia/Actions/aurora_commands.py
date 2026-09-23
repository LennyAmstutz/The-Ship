import json
import time

import paho.mqtt.client as mqtt

from config import MQTT_HOST, MQTT_PORT, AURORA_RX_TOPIC, AURORA_TX_TOPIC

_client = None


def connect(on_message):
    """Verbindet mit dem MQTT-Server und ruft on_message(nachricht) fuer alles auf,
    was Aurora versenden will. paho verbindet sich bei Abbruch selbst neu."""
    global _client

    def _on_connect(client, userdata, flags, reason_code, properties):
        print(f"[aurora] MQTT verbunden ({reason_code}), abonniere {AURORA_RX_TOPIC}", flush=True)
        client.subscribe(AURORA_RX_TOPIC)   # bei jedem (Re-)Connect neu abonnieren

    def _on_message(client, userdata, msg):
        try:
            on_message(json.loads(msg.payload.decode("utf-8")))
        except Exception as exc:
            print("[aurora] Fehler bei eingehender Nachricht:", exc, msg.payload[:100])

    _client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    _client.on_connect = _on_connect
    _client.on_message = _on_message

    while True:
        try:
            _client.connect(MQTT_HOST, MQTT_PORT)
            break
        except OSError:
            print(f"[aurora] MQTT-Server {MQTT_HOST}:{MQTT_PORT} nicht erreichbar, naechster Versuch", flush=True)
            time.sleep(2)
    _client.loop_start()


def send_message(source, data):
    """Stellt eine Nachricht an Aurora zu. data ist schon base64-codiert."""
    _client.publish(AURORA_TX_TOPIC, json.dumps({"src": source, "data": data}))
