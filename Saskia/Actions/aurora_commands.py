import json

from Actions.mqtt_client import MqttClient
from config import MQTT_HOST, MQTT_PORT, AURORA_RX_TOPIC, AURORA_TX_TOPIC

_client = None


def connect(on_message):
    """Verbindet mit dem MQTT-Server und ruft on_message(nachricht) fuer alles auf,
    was Aurora versenden will. Bei Abbruch wird selbst neu verbunden."""
    global _client

    def _on_message(topic, payload):
        on_message(json.loads(payload.decode("utf-8")))

    _client = MqttClient(MQTT_HOST, MQTT_PORT, client_id="saskia-mission5")
    _client.on_message = _on_message
    _client.subscribe(AURORA_RX_TOPIC)
    _client.connect()


def send_message(source, data):
    """Stellt eine Nachricht an Aurora zu. data ist schon base64-codiert."""
    _client.publish(AURORA_TX_TOPIC, json.dumps({"src": source, "data": data}))
