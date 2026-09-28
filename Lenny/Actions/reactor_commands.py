import requests
from config import command

# Kernreaktor: verbrennt Uran aus dem Laderaum, um Energie zu gewinnen.
# Login per OAuth2 wie beim Laser (auth.login("reactor")).


def seconds_left():
    """Wie lange der Reaktor noch laeuft (laut Doku z.B. "33"). None, wenn die Antwort keine Zahl ist."""
    response = requests.get(command["reactor_seconds_left"], timeout=5)
    response.raise_for_status()
    text = response.text.strip()
    try:
        return float(text)
    except ValueError:
        try:
            data = response.json()
            if isinstance(data, dict):
                data = next((v for v in data.values() if isinstance(v, (int, float))), None)
            return float(data) if data is not None else None
        except ValueError:
            return None
