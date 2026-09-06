import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler

TOKEN = os.environ["BOT_TOKEN"]

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": chat_id,
        "text": text
    }).encode()

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        update = json.loads(self.rfile.read(length))

        message = update.get("message", {})
        chat = message.get("chat", {})
        text = message.get("text", "")

        if chat:
            send_message(chat["id"], f"You said: {text}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
