"""Minimal Railway-ready starter server for the Emilia project.

Replace or extend this health-check server with the bot's actual functionality.
"""

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health"):
            self.send_error(404, "Not found")
            return

        body = b"Emilia is running\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Keep standard request logging in Railway's deployment logs.
        super().log_message(format, *args)


def main():
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Emilia health server listening on port {port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
