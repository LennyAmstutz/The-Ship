import socket
import struct
import threading

from config import MQTT_PORT

# Kleiner MQTT-Server ("Broker") fuer Mission 5 - ersetzt Mosquitto.
# Das Comm-Modul und mission_5 verbinden sich beide hierhin; alles, was jemand
# auf ein Topic publisht, wird an alle weitergegeben, die das Topic abonniert haben.
# Unterstuetzt MQTT 3.1.1 und 5, QoS 0/1/2 (weitergegeben wird mit QoS 0).

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


def _distribute(topic, payload):
    with _clients_lock:
        receivers = [(sock, c) for sock, c in _clients.items() if any(_matches(t, topic) for t in c["topics"])]
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
        print(f"[broker] {name} getrennt: {exc}", flush=True)
    finally:
        with _clients_lock:
            _clients.pop(sock, None)
        sock.close()


def _accept_loop(server):
    while True:
        sock, address = server.accept()
        threading.Thread(target=_handle_client, args=(sock, address), daemon=True).start()


def start_mqtt_broker():
    """Startet den MQTT-Server auf Port MQTT_PORT in einem Hintergrund-Thread.
    Laeuft dort schon einer (z.B. Mosquitto), wird einfach dieser benutzt."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(("0.0.0.0", MQTT_PORT))
    except OSError as exc:
        print(f"[broker] Port {MQTT_PORT} schon belegt ({exc}) - benutze den laufenden MQTT-Server.", flush=True)
        server.close()
        return None
    server.listen()
    print(f"[broker] MQTT-Server laeuft auf Port {MQTT_PORT}", flush=True)
    thread = threading.Thread(target=_accept_loop, args=(server,), daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    start_mqtt_broker()
    threading.Event().wait()
