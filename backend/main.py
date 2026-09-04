import os
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        self.wfile.write(b'{"status":"ok","message":"Chinese-Khmer Dubbing API is running"}')

    def log_message(self, format, *args):
        return


port = int(os.environ.get("PORT", 10000))

server = HTTPServer(("0.0.0.0", port), Handler)

print(f"Server running on port {port}")

server.serve_forever()
