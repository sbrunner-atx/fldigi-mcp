"""A small, typed wrapper around fldigi's XML-RPC control interface.

fldigi ships a built-in XML-RPC server (default ``127.0.0.1:7362``). Every
method documented on the fldigi wiki maps to a dotted call such as
``main.get_frequency``. Python's standard-library :mod:`xmlrpc.client` turns an
attribute chain like ``proxy.main.get_frequency()`` into exactly that call, so
this module needs no third-party dependencies.

The rest of the project talks to fldigi only through the :class:`Fldigi` class,
never to raw RPC plumbing. That keeps the MCP server (``server.py``) clean and
makes the client easy to unit-test.
"""

from __future__ import annotations

import os
import xmlrpc.client

from fldigi_mcp import diag

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7362

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _is_loopback(host: str) -> bool:
    return host.strip().lower() in _LOOPBACK


class FldigiError(RuntimeError):
    """Raised when fldigi cannot be reached or an XML-RPC call fails."""


class Fldigi:
    """Connection to a running fldigi instance.

    Host and port default to fldigi's own defaults but can be overridden via
    constructor arguments or the ``FLDIGI_HOST`` / ``FLDIGI_PORT`` environment
    variables. Construction is cheap and does not open a socket — the first
    real call does.
    """

    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        self.host = host or os.environ.get("FLDIGI_HOST", DEFAULT_HOST)
        self.port = int(port or os.environ.get("FLDIGI_PORT", DEFAULT_PORT))
        self.url = f"http://{self.host}:{self.port}/"
        # allow_none=True lets methods that return XML-RPC "nil" come back as
        # Python None instead of raising.
        self._proxy = xmlrpc.client.ServerProxy(self.url, allow_none=True)

    def _guard(self, call, *args):
        """Invoke an RPC call, translating low-level errors into FldigiError.

        ``OSError`` (incl. ``ConnectionRefusedError`` and ``socket.gaierror``)
        means we could not *reach* fldigi, so we raise a structured message with
        host/network detail (see :mod:`fldigi_mcp.diag`) plus, for a non-loopback
        host, a pointer to mcp-host-bridge. ``xmlrpc.client.Fault`` is a
        *post-connect* fault (fldigi got the call and rejected it), so it keeps
        its own message.
        """
        try:
            return call(*args)
        except OSError as exc:
            msg = diag.connection_error(self.host, self.port, exc)
            if not _is_loopback(self.host):
                msg += (
                    " | If this host cannot reach the target (e.g. a sandboxed MCP "
                    "client that only reaches loopback), run the standalone "
                    f"mcp-host-bridge on this machine — `mcp-host-bridge install fldigi "
                    f"--to {self.host}` — and set FLDIGI_HOST to 127.0.0.1. See "
                    "https://github.com/sbrunner-atx/mcp-host-bridge and docs/INSTALL.md. "
                    "Run the `diagnostics` tool for host/network detail."
                )
            raise FldigiError(msg) from exc
        except xmlrpc.client.Fault as exc:
            raise FldigiError(f"fldigi rejected the call: {exc.faultString}") from exc

    def call(self, method: str, *params):
        """Invoke any fldigi XML-RPC method by dotted name (e.g. 'rig.set_mode').

        This is the generic path the grouped MCP tools use, so the whole API is
        reachable without a hand-written wrapper per method. Binary (bytes)
        results are decoded to text defensively.
        """
        target = self._proxy
        for part in method.split("."):
            target = getattr(target, part)
        result = self._guard(target, *params)
        if isinstance(result, xmlrpc.client.Binary):
            return result.data.decode("utf-8", "replace")
        return result

    # -- fldigi.* : application ------------------------------------------------

    def version(self) -> str:
        """Return the program name and version, e.g. ``'fldigi 4.2.11'``."""
        return self._guard(self._proxy.fldigi.name_version)

    def method_names(self) -> list[str]:
        """Return the names of every XML-RPC method this fldigi build exposes."""
        raw = self._guard(self._proxy.fldigi.list)
        names = [m["name"] if isinstance(m, dict) else str(m) for m in raw]
        return sorted(names)

    # -- modem.* : modem selection --------------------------------------------

    def modem_name(self) -> str:
        """Return the name of the currently selected modem, e.g. ``'BPSK31'``."""
        return self._guard(self._proxy.modem.get_name)

    def modem_names(self) -> list[str]:
        """Return all modem names fldigi supports (PSK31, RTTY, Olivia, ...)."""
        return self._guard(self._proxy.modem.get_names)

    # -- main.* : status -------------------------------------------------------

    def frequency(self) -> float:
        """Return the current RF carrier frequency in Hz."""
        return self._guard(self._proxy.main.get_frequency)

    def trx_status(self) -> str:
        """Return the transmit/receive status: ``'rx'``, ``'tx'`` or ``'tune'``."""
        return self._guard(self._proxy.main.get_trx_status)

    # -- modem.* / main.* : control -------------------------------------------

    def set_modem(self, name: str) -> str:
        """Select a modem by name (e.g. ``'BPSK31'``); returns the previous modem."""
        return self._guard(self._proxy.modem.set_by_name, name)

    def signal_quality(self) -> float:
        """Return the current modem signal quality, 0-100."""
        return self._guard(self._proxy.modem.get_quality)

    def set_frequency(self, hz: float) -> float:
        """Set the RF carrier frequency in Hz; returns the previous frequency."""
        return self._guard(self._proxy.main.set_frequency, float(hz))

    def status_field_1(self) -> str:
        """Return fldigi's first status field (typically S/N)."""
        return self._guard(self._proxy.main.get_status1)

    def status_field_2(self) -> str:
        """Return fldigi's second status field."""
        return self._guard(self._proxy.main.get_status2)

    # -- text.* : received & outgoing text ------------------------------------

    def rx_length(self) -> int:
        """Return the number of characters currently in the RX text widget."""
        return self._guard(self._proxy.text.get_rx_length)

    def read_rx(self, start: int = 0, length: int | None = None) -> str:
        """Return decoded text from the RX widget (defaults to everything)."""
        if length is None:
            length = max(0, self.rx_length() - start)
        if length == 0:
            return ""
        data = self._guard(self._proxy.text.get_rx, start, length)
        # fldigi returns bytes (XML-RPC base64). Decode defensively.
        if isinstance(data, xmlrpc.client.Binary):
            return data.data.decode("utf-8", "replace")
        if isinstance(data, bytes):
            return data.decode("utf-8", "replace")
        return str(data)

    def clear_rx(self) -> None:
        """Clear the RX text widget."""
        return self._guard(self._proxy.text.clear_rx)

    def add_tx(self, text: str) -> None:
        """Append text to the TX (outgoing) widget. Does not transmit."""
        return self._guard(self._proxy.text.add_tx, text)

    def clear_tx(self) -> None:
        """Clear the TX widget."""
        return self._guard(self._proxy.text.clear_tx)

    # -- main.* : transmit control --------------------------------------------

    def tx(self) -> None:
        """Key the transmitter and start sending the TX buffer."""
        return self._guard(self._proxy.main.tx)

    def rx(self) -> None:
        """Return to receive."""
        return self._guard(self._proxy.main.rx)

    def tune(self) -> None:
        """Emit a steady tuning carrier (for an ATU); returns to RX with rx()."""
        return self._guard(self._proxy.main.tune)

    def abort(self) -> None:
        """Immediately abort a transmit or tune."""
        return self._guard(self._proxy.main.abort)
