"""Unit tests for the fldigi client helpers and diagnostics (no running fldigi)."""

from __future__ import annotations

import errno
import socket

from fldigi_mcp import diag
from fldigi_mcp.client import _LOOPBACK, Fldigi, FldigiError, _is_loopback

# -- _is_loopback -------------------------------------------------------------


def test_is_loopback_true_cases():
    assert _is_loopback("127.0.0.1")
    assert _is_loopback("localhost")
    assert _is_loopback("::1")


def test_is_loopback_is_case_and_space_insensitive():
    assert _is_loopback("  LocalHost  ")
    assert _is_loopback("127.0.0.1\n")


def test_is_loopback_false_for_lan_and_public():
    assert not _is_loopback("192.168.1.50")
    assert not _is_loopback("10.0.0.1")
    assert not _is_loopback("example.com")


def test_loopback_set_contents():
    assert _LOOPBACK == {"127.0.0.1", "::1", "localhost"}


# -- Fldigi construction (opens no socket) ------------------------------------


def test_construction_resolves_url_without_connecting():
    fl = Fldigi("127.0.0.1", 7362)
    assert fl.host == "127.0.0.1"
    assert fl.port == 7362
    assert fl.url == "http://127.0.0.1:7362/"


# -- structured connection errors via _guard ----------------------------------


def _boom_refused(*_args):
    raise ConnectionRefusedError(errno.ECONNREFUSED, "Connection refused")


def _boom_timeout(*_args):
    raise OSError(errno.ETIMEDOUT, "Connection timed out")


def test_guard_loopback_error_is_structured_without_bridge_hint():
    fl = Fldigi("127.0.0.1", 7362)
    try:
        fl._guard(_boom_refused)
    except FldigiError as exc:
        msg = str(exc)
        assert "Could not reach fldigi" in msg
        assert "target=127.0.0.1:7362" in msg
        assert "errno=ECONNREFUSED" in msg
        assert "mcp-host-bridge" not in msg  # loopback host: no bridge hint
    else:  # pragma: no cover
        raise AssertionError("expected FldigiError")


def test_guard_non_loopback_error_adds_bridge_hint():
    fl = Fldigi("192.168.1.50", 7362)
    try:
        fl._guard(_boom_timeout)
    except FldigiError as exc:
        msg = str(exc)
        assert "target=192.168.1.50:7362" in msg
        assert "errno=ETIMEDOUT" in msg
        assert "mcp-host-bridge install fldigi --to 192.168.1.50" in msg
    else:  # pragma: no cover
        raise AssertionError("expected FldigiError")


# -- diag module --------------------------------------------------------------


def test_errno_name_known_and_gai():
    assert diag.errno_name(ConnectionRefusedError(errno.ECONNREFUSED, "x")) == "ECONNREFUSED"
    assert diag.errno_name(socket.gaierror(-2, "x")) == "ENOTFOUND"


def test_network_interfaces_shape():
    net = diag.network_interfaces()
    assert "hostname" in net
    assert "ipv4_addresses" in net
    assert isinstance(net["ipv4_addresses"], list)


def test_connection_error_mentions_fldigi():
    msg = diag.connection_error("127.0.0.1", 7362, ConnectionRefusedError(errno.ECONNREFUSED, "x"))
    assert msg.startswith("Could not reach fldigi.")
    assert "target=127.0.0.1:7362" in msg
