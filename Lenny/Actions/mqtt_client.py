import socket
import struct
import threading
import time

# Kleiner MQTT-Client (MQTT 3.1.1, QoS 0) direkt ueber TCP - braucht kein paho.
# Jedes MQTT-Paket: 1 Byte Typ/Flags, "Remaining Length" (1-4 Byte), dann der Inhalt.

CONNECT, CONNACK, PUBLISH, SUBSCRIBE, SUBACK, PINGREQ, PINGRESP = 1, 2, 3, 8, 9, 12, 13
KEEP_ALIVE = 60


def _encode_length(length):
    out = bytearray()
    while True:
        byte = length % 128
        length //= 128
        out.append(byte | 0x80 if length else byte)
        if not length:
            return bytes(out)


def _string(text):
    raw = text.encode("utf-8")
    return struct.pack("!H", len(raw)) + raw


def _packet(packet_type, flags, body):
    return bytes([packet_type << 4 | flags]) + _encode_length(len(body)) + body


class MqttClient:
    def __init__(self, host, port, client_id):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.on_message = None           # Funktion (topic, payload_bytes)
        self._topics = []
        self._sock = None
        self._send_lock = threading.Lock()
        self._packet_id = 0

    # --- Verbindung ------------------------------------------------------
    def connect(self):
        """Verbindet (mit Wiederholung) und startet Empfangs- und Ping-Thread."""
        self._connect_until_success()
        threading.Thread(target=self._read_loop, daemon=True).start()
        threading.Thread(target=self._ping_loop, daemon=True).start()

    def _connect_until_success(self):
        while True:
            try:
                self._open()
                return
            except OSError as exc:
                print(f"[mqtt] {self.host}:{self.port} nicht erreichbar ({exc}), naechster Versuch", flush=True)
                time.sleep(2)

    def _open(self):
        sock = socket.create_connection((self.host, self.port), timeout=10)
        body = _string("MQTT") + bytes([4, 0x02]) + struct.pack("!H", KEEP_ALIVE) + _string(self.client_id)
        sock.sendall(_packet(CONNECT, 0, body))

        packet_type, _, data = self._read_packet(sock)
        if packet_type != CONNACK or data[1] != 0:
            sock.close()
            raise OSError(f"CONNECT abgelehnt: {data!r}")
        sock.settimeout(None)
        self._sock = sock
        print(f"[mqtt] verbunden mit {self.host}:{self.port}", flush=True)
        for topic in self._topics:
            self._send_subscribe(topic)

    # --- Senden ----------------------------------------------------------
    def _send(self, data):
        with self._send_lock:
            self._sock.sendall(data)

    def subscribe(self, topic):
        self._topics.append(topic)
        if self._sock is not None:
            self._send_subscribe(topic)

    def _send_subscribe(self, topic):
        self._packet_id = self._packet_id % 65535 + 1
        body = struct.pack("!H", self._packet_id) + _string(topic) + bytes([0])
        self._send(_packet(SUBSCRIBE, 0b0010, body))
        print("[mqtt] abonniert:", topic, flush=True)

    def publish(self, topic, payload):
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        self._send(_packet(PUBLISH, 0, _string(topic) + payload))

    # --- Empfangen -------------------------------------------------------
    @staticmethod
    def _read_exact(sock, count):
        data = b""
        while len(data) < count:
            chunk = sock.recv(count - len(data))
            if not chunk:
                raise ConnectionError("Verbindung vom MQTT-Server geschlossen")
            data += chunk
        return data

    def _read_packet(self, sock):
        """Liest ein ganzes Paket und gibt (typ, flags, inhalt) zurueck."""
        first = self._read_exact(sock, 1)[0]
        length, multiplier = 0, 1
        while True:
            byte = self._read_exact(sock, 1)[0]
            length += (byte & 0x7F) * multiplier
            multiplier *= 128
            if not byte & 0x80:
                break
        return first >> 4, first & 0x0F, self._read_exact(sock, length)

    def _read_loop(self):
        while True:
            try:
                packet_type, flags, body = self._read_packet(self._sock)
            except OSError as exc:
                print("[mqtt] Verbindung weg:", exc, flush=True)
                self._connect_until_success()
                continue

            if packet_type == PUBLISH:
                topic_length = struct.unpack("!H", body[:2])[0]
                topic = body[2:2 + topic_length].decode("utf-8")
                start = 2 + topic_length
                if (flags >> 1) & 0b11:      # QoS > 0: Packet-ID ueberspringen
                    start += 2
                if self.on_message:
                    try:
                        self.on_message(topic, body[start:])
                    except Exception as exc:
                        print("[mqtt] Fehler in on_message:", exc, flush=True)

    def _ping_loop(self):
        while True:
            time.sleep(KEEP_ALIVE / 2)
            try:
                self._send(_packet(PINGREQ, 0, b""))
            except OSError:
                pass
