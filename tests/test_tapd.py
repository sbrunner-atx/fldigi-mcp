"""The host-side tap answers /health and /devices, and signal_hunt with FLDIGI_HUNT_URL
asks it instead of the sound card (served here from a thread with a canned answer)."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

pytest.importorskip("numpy")


def test_health_and_devices_endpoints():
    from fldigi_mcp import tapd

    srv = HTTPServer(("127.0.0.1", 0), tapd.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    import urllib.request

    port = srv.server_address[1]
    h = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/health").read())
    assert h["ok"] is True
    d = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/devices").read())
    assert "devices" in d
    srv.shutdown()


def test_signal_hunt_uses_tap_url(monkeypatch):
    canned = {
        "candidates": [
            {
                "carrier_hz": 1500,
                "mode": "RTTY",
                "shift": 170,
                "fldigi_modem": "RTTY",
                "db_over_floor": 20,
                "score": 30,
            }
        ],
        "seconds": 20,
        "source": "iMic",
    }

    class H(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            body = json.dumps(canned).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            return

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    from fldigi_mcp import server

    monkeypatch.setattr(server.config, "hunt_url", f"http://127.0.0.1:{srv.server_address[1]}")
    out = server.signal_hunt(seconds=20)
    assert out["method"] == "tap"
    assert out["candidates"][0]["fldigi_modem"] == "RTTY"
    out = server.signal_hunt(seconds=20, mode="PSK")
    assert out["candidates"] == []
    srv.shutdown()
