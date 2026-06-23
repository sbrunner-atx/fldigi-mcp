#!/usr/bin/env python3
"""
Phase 0 smoke test for fldigi-mcp.

Goal: prove that this machine can talk to a running fldigi instance over its
XML-RPC interface. This uses ONLY the Python standard library (xmlrpc.client) —
no third-party packages — exactly the way the real MCP server will.

Run it with fldigi open:

    python3 smoke_test.py

You should see fldigi's version, its current modem, frequency, and TX/RX state.
"""

import sys
import xmlrpc.client

# fldigi's XML-RPC server listens here by default. Nothing to configure in
# fldigi — the interface is on out of the box.
FLDIGI_URL = "http://127.0.0.1:7362/"


def main() -> int:
    # A ServerProxy is the "remote control": every attribute access like
    # proxy.main.get_frequency() is turned into an XML-RPC call to fldigi.
    # allow_none=True lets methods that return "nil" come back as Python None
    # instead of raising an error.
    proxy = xmlrpc.client.ServerProxy(FLDIGI_URL, allow_none=True)

    try:
        # --- The actual API calls. Note how the Python names match the wiki
        #     method names exactly: "main.get_frequency" -> proxy.main.get_frequency()
        name_version = proxy.fldigi.name_version()  # e.g. "fldigi 4.2.06"
        method_count = len(proxy.fldigi.list())  # how many API methods this build exposes
        modem = proxy.modem.get_name()  # e.g. "BPSK31"
        freq_hz = proxy.main.get_frequency()  # carrier frequency, in Hz, as a float
        trx = proxy.main.get_trx_status()  # "rx", "tx", or "tune"

    except ConnectionRefusedError:
        print("Could not connect to fldigi at", FLDIGI_URL)
        print("Is fldigi running? Launch it, wait for the main window, then re-run.")
        return 1
    except Exception as exc:  # noqa: BLE001 - smoke test wants a friendly catch-all
        print("Connected, but a call failed:", type(exc).__name__, "-", exc)
        return 2

    # --- Pretty-print what we learned.
    print("Connected to fldigi over XML-RPC")
    print(f"  Version .......... {name_version}")
    print(f"  API methods ...... {method_count}")
    print(f"  Current modem .... {modem}")
    print(f"  Frequency ........ {freq_hz / 1000:.3f} kHz")
    print(f"  TRX state ........ {trx}")
    print()
    print("Success — this Mac can control fldigi. Ready for Phase 1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
