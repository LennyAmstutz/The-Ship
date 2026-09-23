import json
import time

import paho.mqtt.client as mqtt

from config import MQTT_HOST, MQTT_PORT, VESTA_RX_TOPIC, VESTA_TX_TOPIC

_client = None


def connect(on_message):
    """Verbindet mit dem MQTT-Server und ruft on_message(nachricht) fuer alles auf,
    was Vesta versenden will. paho verbindet sich bei Abbruch selbst neu."""
    global _client

    def _on_connect(client, userdata, flags, reason_code, properties):
        print(f"[vesta] MQTT verbunden ({reason_code}), abonniere {VESTA_RX_TOPIC}", flush=True)
        client.subscribe(VESTA_RX_TOPIC)   # bei jedem (Re-)Connect neu abonnieren

    def _on_message(client, userdata, msg):
        try:
            on_message(json.loads(msg.payload.decode("utf-8")))
        except Exception as exc:
            print("[vesta] Fehler bei eingehender Nachricht:", exc, msg.payload[:100])

    _client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    _client.on_connect = _on_connect
    _client.on_message = _on_message

    while True:
        try:
            _client.connect(MQTT_HOST, MQTT_PORT)
            break
        except OSError:
            print(f"[vesta] MQTT-Server {MQTT_HOST}:{MQTT_PORT} nicht erreichbar, naechster Versuch", flush=True)
            time.sleep(2)
    _client.loop_start()


def send_message(source, data):
    """Stellt eine Nachricht an Vesta zu. data ist schon base64-codiert."""
    _client.publish(VESTA_TX_TOPIC, json.dumps({"src": source, "data": data}))
