import socket
import struct
import threading
from urllib.parse import quote

from Actions.hpack_codec import Decoder, encode_headers

# Kleiner gRPC-Server fuer Mission 7 - ersetzt grpcio, das auf dem Schiff fehlt.
# gRPC laeuft ueber HTTP/2 (hier unverschluesselt, "h2c"). Pro Aufruf schickt der Client:
#   HEADERS (:path = /paket.Service/methode) + DATA (5 Bytes Laenge + Protobuf-Nachricht)
# und bekommt zurueck:
#   HEADERS (:status 200) + DATA (Antwort) + HEADERS mit grpc-status (die "Trailer").
# Unterstuetzt nur unaere Aufrufe (eine Anfrage, eine Antwort) - mehr braucht der Analyzer nicht.

PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"

DATA, HEADERS, PRIORITY, RST_STREAM, SETTINGS, PUSH_PROMISE, PING, GOAWAY, WINDOW_UPDATE, CONTINUATION = range(10)
END_STREAM, ACK, END_HEADERS, PADDED, PRIORITY_FLAG = 0x1, 0x1, 0x4, 0x8, 0x20

GRPC_OK, GRPC_UNKNOWN, GRPC_UNIMPLEMENTED, GRPC_UNAVAILABLE = 0, 2, 12, 14


class GrpcError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def _frame(frame_type, flags, stream_id, payload=b""):
    return struct.pack("!I", len(payload))[1:] + bytes([frame_type, flags]) + struct.pack("!I", stream_id) + payload


def _grpc_message(text):
    """grpc-message ist prozent-codiert (alles ausserhalb von ASCII 0x20-0x7E und '%')."""
    return quote(text, safe="".join(chr(c) for c in range(0x20, 0x7F) if chr(c) != "%"))


class _Connection:
    def __init__(self, sock, address, handlers):
        self.sock = sock
        self.peer = f"{address[0]}:{address[1]}"
        self.handlers = handlers
        self.decoder = Decoder()
        self.streams = {}                    # stream_id -> {"block", "headers", "data", "ended"}
        self.write_lock = threading.Lock()
        # Flusskontrolle fuer das, was WIR senden: der Client sagt, wie viel er aufnehmen kann
        self.window_lock = threading.Condition()
        self.max_frame = 16384
        self.initial_window = 65535
        self.conn_window = 65535
        self.stream_windows = {}             # stream_id -> freies Fenster (None = abgebrochen)

    def send(self, *frames):
        with self.write_lock:
            self.sock.sendall(b"".join(frames))

    def _read_exact(self, count):
        data = b""
        while len(data) < count:
            chunk = self.sock.recv(count - len(data))
            if not chunk:
                raise ConnectionError("Client hat die Verbindung geschlossen")
            data += chunk
        return data

    # --- Antworten ---------------------------------------------------------

    def _send_data(self, stream_id, body):
        """DATA in Stuecken, die in Frame-Groesse und Flusskontroll-Fenster des Clients passen."""
        while body:
            with self.window_lock:
                ok = self.window_lock.wait_for(
                    lambda: self.stream_windows.get(stream_id) is None
                    or min(self.conn_window, self.stream_windows[stream_id]) > 0, timeout=30)
                window = self.stream_windows.get(stream_id)
                if window is None:
                    raise ConnectionError("Stream wurde vom Client abgebrochen")
                if not ok:
                    raise TimeoutError("Client nimmt keine Daten mehr an")
                size = min(len(body), self.max_frame, self.conn_window, window)
                self.conn_window -= size
                self.stream_windows[stream_id] -= size
            self.send(_frame(DATA, 0, stream_id, body[:size]))
            body = body[size:]

    def _respond(self, stream_id, headers, data):
        path = dict(headers).get(":path", "")
        try:
            handler = self.handlers.get(path)
            if handler is None:
                raise GrpcError(GRPC_UNIMPLEMENTED, f"Methode {path} gibt es nicht")
            if len(data) < 5:
                raise GrpcError(GRPC_UNKNOWN, "leere Anfrage")
            compressed, length = struct.unpack("!BI", data[:5])
            if compressed:
                raise GrpcError(GRPC_UNIMPLEMENTED, "komprimierte Nachrichten werden nicht unterstuetzt")
            answer = handler(bytes(data[5:5 + length]))
            body = struct.pack("!BI", 0, len(answer)) + answer
            self.send(_frame(HEADERS, END_HEADERS, stream_id,
                             encode_headers([(":status", "200"), ("content-type", "application/grpc")])))
            self._send_data(stream_id, body)
            self.send(_frame(HEADERS, END_HEADERS | END_STREAM, stream_id,
                             encode_headers([("grpc-status", GRPC_OK), ("grpc-message", "")])))
        except (OSError, ConnectionError, TimeoutError) as exc:
            print(f"[grpc] Antwort an {self.peer} abgebrochen: {exc}", flush=True)
        except Exception as exc:
            status = exc.status if isinstance(exc, GrpcError) else GRPC_UNKNOWN
            print(f"[grpc] {path} von {self.peer}: Fehler {status}: {exc}", flush=True)
            try:
                self.send(_frame(HEADERS, END_HEADERS | END_STREAM, stream_id, encode_headers([
                    (":status", "200"), ("content-type", "application/grpc"),
                    ("grpc-status", status), ("grpc-message", _grpc_message(str(exc)))])))
            except OSError:
                pass
        finally:
            with self.window_lock:
                self.stream_windows.pop(stream_id, None)

    def _finish_if_ready(self, stream_id):
        stream = self.streams.get(stream_id)
        if stream and stream["headers"] is not None and stream["ended"]:
            del self.streams[stream_id]
            threading.Thread(target=self._respond, args=(stream_id, stream["headers"], stream["data"]),
                             daemon=True).start()

    # --- Frames lesen --------------------------------------------------------

    def _on_headers(self, flags, stream_id, payload, continuation=False):
        if stream_id not in self.streams:
            self.streams[stream_id] = {"block": b"", "headers": None, "data": bytearray(), "ended": False}
            with self.window_lock:
                self.stream_windows[stream_id] = self.initial_window
        stream = self.streams[stream_id]
        if not continuation:
            pad = 0
            if flags & PADDED:
                pad, payload = payload[0], payload[1:]
            if flags & PRIORITY_FLAG:
                payload = payload[5:]
            payload = payload[:len(payload) - pad]
            if flags & END_STREAM:
                stream["ended"] = True
        stream["block"] += payload
        if flags & END_HEADERS:
            headers = self.decoder.decode(stream["block"])
            stream["block"] = b""
            if stream["headers"] is None:
                stream["headers"] = headers            # sonst sind es Trailer vom Client - egal
            self._finish_if_ready(stream_id)

    def _on_data(self, flags, stream_id, payload):
        if payload:                                    # Flusskontrolle: gelesene Bytes wieder freigeben
            increment = struct.pack("!I", len(payload))
            frames = [_frame(WINDOW_UPDATE, 0, 0, increment)]
            if not flags & END_STREAM:
                frames.append(_frame(WINDOW_UPDATE, 0, stream_id, increment))
            self.send(*frames)
        stream = self.streams.get(stream_id)
        if stream is None:
            return
        if flags & PADDED:
            payload = payload[1:len(payload) - payload[0]]
        stream["data"] += payload
        if flags & END_STREAM:
            stream["ended"] = True
            self._finish_if_ready(stream_id)

    def _on_settings(self, payload):
        with self.window_lock:
            for pos in range(0, len(payload) - 5, 6):
                key, value = struct.unpack("!HI", payload[pos:pos + 6])
                if key == 4:                               # INITIAL_WINDOW_SIZE gilt auch fuer offene Streams
                    delta = value - self.initial_window
                    self.initial_window = value
                    for sid, window in self.stream_windows.items():
                        if window is not None:
                            self.stream_windows[sid] = window + delta
                elif key == 5:                             # MAX_FRAME_SIZE
                    self.max_frame = value
            self.window_lock.notify_all()

    def _on_window_update(self, stream_id, payload):
        increment = struct.unpack("!I", payload)[0] & 0x7FFFFFFF
        with self.window_lock:
            if stream_id == 0:
                self.conn_window += increment
            elif self.stream_windows.get(stream_id) is not None:
                self.stream_windows[stream_id] += increment
            self.window_lock.notify_all()

    def serve(self):
        try:
            if self._read_exact(len(PREFACE)) != PREFACE:
                print(f"[grpc] {self.peer} spricht kein HTTP/2 - Verbindung zu", flush=True)
                return
            self.send(_frame(SETTINGS, 0, 0, struct.pack("!HI", 3, 100)))   # max. 100 Streams gleichzeitig
            last_headers_stream = 0
            while True:
                header = self._read_exact(9)
                length = struct.unpack("!I", b"\x00" + header[:3])[0]
                frame_type, flags = header[3], header[4]
                stream_id = struct.unpack("!I", header[5:9])[0] & 0x7FFFFFFF
                payload = self._read_exact(length)

                if frame_type == HEADERS:
                    last_headers_stream = stream_id
                    self._on_headers(flags, stream_id, payload)
                elif frame_type == CONTINUATION:
                    self._on_headers(flags, last_headers_stream, payload, continuation=True)
                elif frame_type == DATA:
                    self._on_data(flags, stream_id, payload)
                elif frame_type == SETTINGS and not flags & ACK:
                    self._on_settings(payload)
                    self.send(_frame(SETTINGS, ACK, 0))
                elif frame_type == WINDOW_UPDATE:
                    self._on_window_update(stream_id, payload)
                elif frame_type == PING and not flags & ACK:
                    self.send(_frame(PING, ACK, 0, payload))
                elif frame_type == RST_STREAM:
                    waiting = self.streams.pop(stream_id, None) is not None   # Antwort noch nicht gestartet
                    with self.window_lock:
                        if waiting:
                            self.stream_windows.pop(stream_id, None)
                        elif stream_id in self.stream_windows:
                            self.stream_windows[stream_id] = None             # laufende Antwort abbrechen
                        self.window_lock.notify_all()
                elif frame_type == GOAWAY:
                    return
                # PRIORITY, SETTINGS-ACK, PING-ACK und Unbekanntes: nichts zu tun
        except (OSError, ConnectionError):
            pass
        except Exception as exc:
            print(f"[grpc] Fehler mit {self.peer}: {exc!r}", flush=True)
            try:
                self.send(_frame(GOAWAY, 0, 0, struct.pack("!II", 0, 1)))   # PROTOCOL_ERROR
            except OSError:
                pass
        finally:
            self.sock.close()


def start_grpc_server(port, handlers, host="0.0.0.0"):
    """Startet den gRPC-Server im Hintergrund. handlers: {"/paket.Service/methode": funktion(bytes) -> bytes}"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen()
    print(f"[grpc] gRPC-Server laeuft auf Port {port}: {', '.join(handlers)}", flush=True)

    def accept_loop():
        while True:
            sock, address = server.accept()
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            threading.Thread(target=_Connection(sock, address, handlers).serve, daemon=True).start()

    threading.Thread(target=accept_loop, daemon=True).start()
    return server
