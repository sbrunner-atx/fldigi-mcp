#!/usr/bin/env python3
"""Regenerate src/fldigi_mcp/data/fldigi_methods.json from a running fldigi.

    uv run python scripts/refresh_method_catalog.py [host] [port]

The catalog is what tests/test_coverage.py holds the connector to. After a
fldigi release, run this against the new build, run the tests, and wire whatever
the failing test names. fldigi.list may repeat a row (4.2.x lists log.set_rst_in
and log.set_rst_out twice); duplicates are dropped here.
"""

import datetime as dt
import json
import pathlib
import sys
import xmlrpc.client

host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 7362
f = xmlrpc.client.ServerProxy(f"http://{host}:{port}/", allow_none=True)
version = f.fldigi.version()
seen, methods = set(), []
for m in f.fldigi.list():
    if m["name"] in seen:
        continue
    seen.add(m["name"])
    methods.append({"name": m["name"], "signature": m["signature"], "help": m["help"]})
root = pathlib.Path(__file__).resolve().parents[1]
out = root / "src" / "fldigi_mcp" / "data" / "fldigi_methods.json"
out.write_text(
    json.dumps(
        {
            "fldigi_version": version,
            "verified": dt.date.today().isoformat(),
            "note": "fldigi.list output, duplicates dropped; see tests/test_coverage.py",
            "methods": methods,
        },
        indent=1,
    )
    + "\n"
)
print(f"wrote {len(methods)} methods from fldigi {version} to {out}")
