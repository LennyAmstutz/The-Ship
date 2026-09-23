"""Sucht auf Saskias Schiff das Comm Module Aurora.

    python3 probe_aurora.py

Probiert alle Ports 2000-2099 auf dem eigenen Schiff, meldet die offenen und
zeigt fuer jeden die ersten Bytes, die der Port von sich aus schickt
(als Hex, als Text und XOR 0xAA - so war das Vesta-Format verschluesselt).
Die Ausgabe bitte komplett an Claude schicken.
"""
import socket

from config import HOST

# Ports, deren Dienst wir schon kennen
KNOWN = {
    2000: "cockpit_frontend", 2001: "cockpit_backend", 2002: "cockpit_backend",
    2003: "thruster", 2004: "thruster", 2005: "thruster", 2006: "thruster",
    2007: "thruster", 2008: "thruster", 2009: "easy_steering", 2010: "navigation",
    2011: "communication", 2012: "cargo_hold", 2014: "rabbitmq", 2018: "laser",
    2036: "unser MQTT-Server", 2040: "whatsupp", 2060: "cockpit_backend",
}


def show(label, data):
    print(f"      {label:5} {data}")


def probe(port):
    try:
        sock = socket.create_connection((HOST, port), timeout=1)
    except OSError:
        return False

    print(f"\n[offen] {HOST}:{port}  ({KNOWN.get(port, 'UNBEKANNT - evtl. Comm Module Aurora')})")
    sock.settimeout(3)
    try:
        data = sock.recv(4096)
    except socket.timeout:
        data = None
    except OSError as exc:
        print("      Fehler beim Lesen:", exc)
        data = None
    finally:
        sock.close()

    if data is None:
        print("      sendet von sich aus nichts (wartet vermutlich auf uns)")
    elif not data:
        print("      Verbindung sofort wieder geschlossen")
    else:
        print(f"      {len(data)} Bytes empfangen:")
        show("hex", data[:64].hex(" "))
        show("text", data[:120].decode("utf-8", "replace"))
        show("xor", bytes(b ^ 0xAA for b in data[:120]).decode("utf-8", "replace"))
    return True


if __name__ == "__main__":
    print(f"Suche offene Ports auf {HOST} (2000-2099) ...")
    found = [port for port in range(2000, 2100) if probe(port)]
    unknown = [port for port in found if port not in KNOWN]
    print("\nOffene Ports:", found)
    print("Unbekannte Ports (Kandidaten fuer Comm Module Aurora):", unknown or "keine")
