import requests
from config import command

# Energy-Management im Aktiv/Passiv-Modus: 2 Nodes, immer genau einer ist aktiv.
# Lesen geht bei beiden, schreiben nur beim aktiven Node.


def status(node):
    response = requests.get(f"{node}/status", timeout=5)
    response.raise_for_status()
    return response.json()


def active_node():
    """Fragt beide Nodes nach ihrer Rolle und gibt die URL des aktiven zurueck."""
    for node in command["energy_nodes"]:
        try:
            if status(node).get("role") == "active":
                return node
        except requests.RequestException as exc:
            print(f"[energy] {node} nicht erreichbar: {exc}")
    raise RuntimeError("kein aktiver Energy-Management-Node gefunden")


def limits(node=None):
    """Aktuelle Limits - geht auch beim passiven Node."""
    nodes = [node] if node else command["energy_nodes"]
    for candidate in nodes:
        try:
            response = requests.get(f"{candidate}/limits", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
    raise last_error


def set_limits(changes):
    """Setzt die Limits auf dem aktiven Node. Wechselt der aktive Node genau dazwischen,
    wird der andere probiert. Gibt die URL des Nodes zurueck, der geschrieben hat."""
    first = active_node()
    others = [n for n in command["energy_nodes"] if n != first]
    for node in [first] + others:
        new_limits = {**limits(node), **changes}
        try:
            response = requests.put(f"{node}/limits", json=new_limits, timeout=5)
            if response.ok and response.json().get("kind") == "success":
                return node
            print(f"[energy] {node} lehnt ab: {response.status_code} {response.text.strip()}")
        except requests.RequestException as exc:
            print(f"[energy] {node} nicht erreichbar: {exc}")
    raise RuntimeError("Limits konnten auf keinem Node gesetzt werden")
