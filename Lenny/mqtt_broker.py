import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

from config import MQTT_PORT

# Kleiner MQTT-Server ("Broker") fuer Mission 5 - ersetzt Mosquitto.
# Das Comm-Modul und mission_5 verbinden sich beide hierhin; alles, was jemand
# auf ein Topic publisht, wird an alle weitergegeben, die das Topic abonniert haben.
# Unterstuetzt MQTT 3.1.1 und 5, QoS 0/1/2 (weitergegeben wird mit QoS 0).
#
# Der Server laeuft als EIGENER Prozess weiter, auch wenn main.py beendet/neu gestartet
# wird: Das Comm-Modul verbindet sich nach einem Server-Neustart zwar selbst neu,
# abonniert aber nicht nochmals - dann kaeme bei Vesta nichts mehr an.
# Log: mqtt_broker.log (mission_5 zeigt es mit an). Stoppen: pkill -f mqtt_broker.py

CONNECT, CONNACK, PUBLISH, PUBACK, PUBREC, PUBREL, PUBCOMP = 1, 2, 3, 4, 5, 6, 7
SUBSCRIBE, SUBACK, UNSUBSCRIBE, UNSUBACK, PINGREQ, PINGRESP, DISCONNECT = 8, 9, 10, 11, 12, 13, 14

_clients = {}            # socket -> {"name", "version", "topics", "lock"}
_clients_lock = threading.Lock()


def _encode_length(length):
    out = bytearray()
    while True:
        byte = length % 128
        length //= 128
        out.append(byte | 0x80 if length else byte)
        if not length:
            return bytes(out)


def _decode_length(data, pos):
    """Variable Laenge (auch fuer MQTT-5-Properties). Gibt (wert, neue_position) zurueck."""
    value, multiplier = 0, 1
    while True:
        byte = data[pos]
        pos += 1
        value += (byte & 0x7F) * multiplier
        multiplier *= 128
        if not byte & 0x80:
            return value, pos


def _string(text):
    raw = text.encode("utf-8")
    return struct.pack("!H", len(raw)) + raw


def _read_string(data, pos):
    length = struct.unpack("!H", data[pos:pos + 2])[0]
    return data[pos + 2:pos + 2 + length].decode("utf-8"), pos + 2 + length


def _packet(packet_type, flags, body):
    return bytes([packet_type << 4 | flags]) + _encode_length(len(body)) + body


def _read_exact(sock, count):
    data = b""
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise ConnectionError("Client hat die Verbindung geschlossen")
        data += chunk
    return data


def _read_packet(sock):
    first = _read_exact(sock, 1)[0]
    length, multiplier = 0, 1
    while True:
        byte = _read_exact(sock, 1)[0]
        length += (byte & 0x7F) * multiplier
        multiplier *= 128
        if not byte & 0x80:
            break
    return first >> 4, first & 0x0F, _read_exact(sock, length)


def _matches(pattern, topic):
    """Topic-Filter mit Wildcards: + = eine Ebene, # = alles darunter."""
    pattern_parts, topic_parts = pattern.split("/"), topic.split("/")
    for i, part in enumerate(pattern_parts):
        if part == "#":
            return True
        if i >= len(topic_parts) or (part != "+" and part != topic_parts[i]):
            return False
    return len(pattern_parts) == len(topic_parts)


def _send(sock, data):
    client = _clients.get(sock)
    if client is None:
        return
    with client["lock"]:
        sock.sendall(data)


_warned_topics = set()


def _distribute(topic, payload):
    with _clients_lock:
        receivers = [(sock, c) for sock, c in _clients.items() if any(_matches(t, topic) for t in c["topics"])]
    if not receivers:
        if topic not in _warned_topics:
            _warned_topics.add(topic)
            with _clients_lock:
                subscribed = {c["name"]: c["topics"] for c in _clients.values()}
            print(f"[broker] WARNUNG: niemand hat '{topic}' abonniert - die Nachricht geht verloren. "
                  f"Abos gerade: {subscribed}", flush=True)
        return
    _warned_topics.discard(topic)
    for sock, client in receivers:
        body = _string(topic) + (b"\x00" if client["version"] == 5 else b"") + payload
        try:
            _send(sock, _packet(PUBLISH, 0, body))
        except OSError:
            pass


def _handle_connect(sock, body):
    _, pos = _read_string(body, 0)                 # Protokollname "MQTT"
    version = body[pos]
    pos += 4                                       # Version, Flags, Keep-Alive
    if version == 5:
        props, pos = _decode_length(body, pos)
        pos += props
    name, _ = _read_string(body, pos)

    with _clients_lock:
        _clients[sock] = {"name": name or "?", "version": version, "topics": [], "lock": threading.Lock()}
    reply = b"\x00\x00\x00" if version == 5 else b"\x00\x00"   # Session-Flag, Reason 0 (+ leere Properties)
    _send(sock, _packet(CONNACK, 0, reply))
    print(f"[broker] {name} verbunden (MQTT {'5' if version == 5 else '3.1.1'})", flush=True)
    return version


def _handle_client(sock, address):
    version = 4
    name = f"{address[0]}:{address[1]}"
    try:
        packet_type, flags, body = _read_packet(sock)
        if packet_type != CONNECT:
            return
        version = _handle_connect(sock, body)
        name = _clients[sock]["name"]

        while True:
            packet_type, flags, body = _read_packet(sock)

            if packet_type == PUBLISH:
                qos = (flags >> 1) & 0b11
                topic, pos = _read_string(body, 0)
                packet_id = None
                if qos:
                    packet_id = body[pos:pos + 2]
                    pos += 2
                if version == 5:
                    props, pos = _decode_length(body, pos)
                    pos += props
                if qos == 1:
                    _send(sock, _packet(PUBACK, 0, packet_id))
                elif qos == 2:
                    _send(sock, _packet(PUBREC, 0, packet_id))
                _distribute(topic, body[pos:])

            elif packet_type == PUBREL:
                _send(sock, _packet(PUBCOMP, 0, body[:2]))

            elif packet_type == SUBSCRIBE:
                packet_id, pos = body[:2], 2
                if version == 5:
                    props, pos = _decode_length(body, pos)
                    pos += props
                granted = bytearray()
                while pos < len(body):
                    topic, pos = _read_string(body, pos)
                    pos += 1                                  # gewuenschte QoS / Optionen
                    _clients[sock]["topics"].append(topic)
                    granted.append(0)                         # wir liefern mit QoS 0
                    print(f"[broker] {name} abonniert {topic}", flush=True)
                _send(sock, _packet(SUBACK, 0, packet_id + (b"\x00" if version == 5 else b"") + bytes(granted)))

            elif packet_type == UNSUBSCRIBE:
                packet_id, pos = body[:2], 2
                if version == 5:
                    props, pos = _decode_length(body, pos)
                    pos += props
                count = 0
                while pos < len(body):
                    topic, pos = _read_string(body, pos)
                    if topic in _clients[sock]["topics"]:
                        _clients[sock]["topics"].remove(topic)
                    count += 1
                reply = packet_id + (b"\x00" + bytes(count) if version == 5 else b"")
                _send(sock, _packet(UNSUBACK, 0, reply))

            elif packet_type == PINGREQ:
                _send(sock, _packet(PINGRESP, 0, b""))

            elif packet_type == DISCONNECT:
                break
    except (OSError, IndexError, struct.error, UnicodeDecodeError) as exc:
        if sock in _clients:                      # Verbindungstests ohne CONNECT nicht melden
            print(f"[broker] {name} getrennt: {exc}", flush=True)
    finally:
        with _clients_lock:
            _clients.pop(sock, None)
        sock.close()


def _accept_loop(server):
    while True:
        sock, address = server.accept()
        threading.Thread(target=_handle_client, args=(sock, address), daemon=True).start()


LOG_FILE = Path(__file__).with_name("mqtt_broker.log")


def _serve_forever():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", MQTT_PORT))
    server.listen()
    print(f"[broker] MQTT-Server laeuft auf Port {MQTT_PORT}", flush=True)
    _accept_loop(server)


def _is_running():
    try:
        socket.create_connection(("127.0.0.1", MQTT_PORT), timeout=1).close()
        return True
    except OSError:
        return False


def _follow_log(start):
    """Zeigt neue Zeilen aus mqtt_broker.log in der Ausgabe von main.py an."""
    with open(LOG_FILE, encoding="utf-8", errors="replace") as log:
        log.seek(start)
        while True:
            line = log.readline()
            if line:
                print(line, end="", flush=True)
            else:
                time.sleep(0.3)


def start_mqtt_broker():
    """Startet den MQTT-Server als eigenen Hintergrund-Prozess, falls er noch nicht laeuft.
    Laeuft auf dem Port schon einer (unser alter Prozess oder z.B. Mosquitto), wird dieser benutzt."""
    LOG_FILE.touch()
    start = LOG_FILE.stat().st_size
    if _is_running():
        print(f"[broker] MQTT-Server laeuft schon auf Port {MQTT_PORT} - benutze ihn (Abos bleiben erhalten).", flush=True)
    else:
        with open(LOG_FILE, "a") as log:
            subprocess.Popen([sys.executable, "-u", str(Path(__file__).resolve())],
                             cwd=str(Path(__file__).parent), stdout=log, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        for _ in range(50):
            if _is_running():
                break
            time.sleep(0.1)
        else:
            raise RuntimeError(f"MQTT-Server startet nicht - siehe {LOG_FILE}")
    threading.Thread(target=_follow_log, args=(start,), daemon=True).start()


if __name__ == "__main__":
    _serve_forever()
