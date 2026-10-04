"""JioFarm — Native Threading HTTP Server for Local Web Panel."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from jiofarm.config import load_config
from jiofarm.engine import FarmController
from jiofarm.hunter import create_provider
from jiofarm.services.registry import list_services

WEB_DIR = Path(__file__).resolve().parent
HTML_FILE = WEB_DIR / "index.html"


class FarmRequestHandler(BaseHTTPRequestHandler):
    """Handles REST API and static UI delivery for the local web panel."""

    def log_message(self, format: str, *args: object) -> None:
        # Suppress noisy standard HTTP access logs in console
        pass

    def _send_json(self, data: object, status: int = 200) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length).decode("utf-8")
            return json.loads(body)
        return {}

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        ctrl = FarmController.get_instance()

        if path in ("/", "/index.html"):
            if not HTML_FILE.exists():
                self.send_error(404, "HTML file missing")
                return
            content = HTML_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/api/status":
            self._send_json(ctrl.get_status())
            return

        if path == "/api/services":
            self._send_json(list_services())
            return

        if path == "/api/balance":
            qs = parse_qs(parsed.query)
            provider_req = qs.get("provider", [ctrl.provider_name])[0]
            try:
                cfg = load_config()
                cfg.provider = provider_req
                prov = create_provider(cfg)
                bal = prov.balance()
                self._send_json({"success": True, "balance": bal})
            except Exception as e:
                self._send_json({"success": False, "error": str(e), "balance": 0.0})
            return

        if path == "/api/links":
            links = ctrl.store.export_links()
            self._send_json({"success": True, "links": links})
            return

        self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        ctrl = FarmController.get_instance()

        if path == "/api/start":
            body = self._read_json()
            success = ctrl.start(
                service_id=body.get("service_id", "jio-google"),
                provider_name=body.get("provider_name"),
                concurrency=body.get("concurrency"),
                max_price=body.get("max_price"),
                count=body.get("count"),
                target=body.get("target"),
                proxy_url=body.get("proxy_url"),
            )
            self._send_json({"success": success})
            return

        if path == "/api/stop":
            ctrl.stop()
            self._send_json({"success": True})
            return

        self.send_error(404, "Not Found")


def run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Start the native web panel HTTP server."""
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, FarmRequestHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
