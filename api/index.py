from http.server import BaseHTTPRequestHandler
import json

from analyze import analyze
from obfuscate import StrongObfuscator


class handler(BaseHTTPRequestHandler):

    def _send(self, status, data):
        body = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Methods",
            "POST, OPTIONS"
        )
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )
        self.send_header(
            "Content-Length",
            str(len(body))
        )
        self.end_headers()

        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(200, {"ok": True})

    def do_POST(self):
        try:
            length = int(
                self.headers.get("Content-Length", "0")
            )

            body = self.rfile.read(length)

            data = json.loads(
                body.decode("utf-8")
            )

            code = data.get("code", "")

            if not isinstance(code, str) or not code.strip():
                self._send(
                    400,
                    {"error": "No code provided"}
                )
                return

            if self.path.endswith("/analyze"):
                result = analyze(code)

            elif self.path.endswith("/obfuscate"):
                obfuscator = StrongObfuscator(code)
                result_code = obfuscator.obfuscate_aggressive()

                result = {
                    "result": result_code
                }

            else:
                self._send(
                    404,
                    {"error": "Unknown endpoint"}
                )
                return

            self._send(200, result)

        except json.JSONDecodeError:
            self._send(
                400,
                {"error": "Invalid JSON"}
            )

        except Exception as exc:
            self._send(
                500,
                {"error": str(exc)}
            )

    def do_GET(self):
        self._send(
            405,
            {"error": "Use POST"}
        )
