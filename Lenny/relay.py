from flask import Flask, request
import websocket, requests, threading, json

MY_STATION = "Elyse Terminal"
COMM = "ws://192.168.101.50:2026/api"
PEERS = {
    "Core Station": "http://192.168.101.51:5000",
}

app = Flask(__name__)
ws = websocket.WebSocket()

@app.post("/msg")
def msg():
    d = request.json
    ws.send(json.dumps({"source": MY_STATION, "msg": d["msg"]}))
    print("-> Station:", d["msg"])
    return "ok"

def loop():
    ws.connect(COMM)
    print("connected")
    while True:
        d = json.loads(ws.recv())
        print("<- Station:", d)
        peer = PEERS.get(d.get("destination"))
        if peer:
            try:
                requests.post(peer + "/msg", json=d, timeout=3)
                print("-> Peer:", peer)
            except Exception as e:
                print(e)

threading.Thread(target=loop, daemon=True).start()
app.run(host="0.0.0.0", port=5000)