import http.server
import socketserver
import os
import json
import http.client


BRIDGE_THREAD_ID = int(os.environ.get("BRIDGE_THREAD_ID"))
TELEGRAM_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID"))
TELEGRAM_CHAT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

class QqToTelegramForwardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Hello")

    def do_POST(self):
        content_length_str = self.headers.get("Content-Length")
        content_length = int(content_length_str) if content_length_str else 0

        body = self.rfile.read(content_length)
        if not body:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Bad Request: No body")
            return
        try:
            loaded = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Bad Request: Invalid JSON")
            return
        print(f"Received JSON: {loaded}")
        nickname = loaded.get("sender", {}).get("nickname")
        message = loaded.get("raw_message", None)
        if not nickname or not message:
            print(f"Missing nickname or message in the JSON payload: {loaded}")
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Bad Request: Missing nickname or message")
            return
        conn = http.client.HTTPSConnection("api.telegram.org", 443)
        token = TELEGRAM_CHAT_TOKEN
        chat_id = TELEGRAM_CHAT_ID
        conn.request(
            "POST",
            f"/bot{token}/sendMessage",
            json.dumps(
                {
                    "chat_id": chat_id,
                    "text": f"[{nickname}]: {message}",
                    "reply_to_message_id": BRIDGE_THREAD_ID,
                }
            ),
            {"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        print(f"Telegram API response: {response.status} {response.reason}")
        conn.close()


def run(
    server_class=socketserver.TCPServer,
    handler_class=QqToTelegramForwardHandler,
    port=int(os.environ.get("PORT", 8881)),
):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    try:
        httpd.serve_forever()
    finally:
        print("Shutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    run()
