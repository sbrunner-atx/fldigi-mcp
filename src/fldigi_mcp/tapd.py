"""fldigi-mcp-tap: a tiny HTTP service that runs where the audio is.

The MCP server does not always run on the machine that hears the receiver: the
Cowork sandbox has no LAN, and fldigi may live on a VM reached through
mcp-host-bridge. This service runs beside fldigi, taps the input device, runs
the same analyser as `signal_hunt`, and answers over plain HTTP, so the server
sets FLDIGI_HUNT_URL (e.g. http://127.0.0.1:7365) and asks it instead of the
sound card. Read-only: it never touches fldigi and never transmits.

    fldigi-mcp-tap [--port 7365] [--device iMic] [--bind 127.0.0.1]
    GET /hunt?seconds=20&top=4&lo=300&hi=3400   -> JSON {candidates, seconds, source}
    GET /devices                                -> JSON {devices}
    GET /health                                 -> JSON {ok, device}

Bind to 127.0.0.1 unless the caller is on another host; there is no
authentication, and a caller can occupy the audio device for `seconds`.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from fldigi_mcp import hunt

DEVICE: str | None = None


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/health":
                self._send(200, {"ok": True, "device": DEVICE or "default"})
            elif u.path == "/devices":
                self._send(200, {"devices": hunt.list_devices()})
            elif u.path == "/hunt":
                seconds = min(120.0, max(2.0, float(q.get("seconds", 20))))
                x, fs = hunt.capture(seconds, q.get("device") or DEVICE)
                if float((x**2).mean()) == 0.0:
                    self._send(
                        200,
                        {
                            "candidates": [],
                            "seconds": seconds,
                            "source": DEVICE or "default",
                            "warning": "audio is all zeros: the input device is silent or this "
                            "process has no microphone permission",
                        },
                    )
                    return
                cands = hunt.analyse(
                    x,
                    fs,
                    lo=float(q.get("lo", 300)),
                    hi=float(q.get("hi", 3400)),
                    top=int(q.get("top", 4)),
                )
                self._send(
                    200, {"candidates": cands, "seconds": seconds, "source": DEVICE or "default"}
                )
            else:
                self._send(404, {"error": "unknown path"})
        except Exception as exc:  # report, never die
            self._send(500, {"error": f"{type(exc).__name__}: {exc}"})

    def log_message(self, fmt, *args):  # quiet
        return


def main() -> None:
    global DEVICE
    ap = argparse.ArgumentParser(description="host-side audio tap for fldigi-mcp signal_hunt")
    ap.add_argument("--port", type=int, default=7365)
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--device", default=None, help="input device name substring or index")
    a = ap.parse_args()
    DEVICE = a.device
    print(f"fldigi-mcp-tap on http://{a.bind}:{a.port} device={DEVICE or 'default'}")
    HTTPServer((a.bind, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
