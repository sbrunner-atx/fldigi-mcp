"""Unit tests for the grouped-tool operation maps and resolver."""

from __future__ import annotations

import pytest

from fldigi_mcp import methods
from fldigi_mcp.methods import KEYING_METHODS, VALID_KINDS, UnknownOperation, coerce, resolve

ALL_MAPS = [
    methods.STATION_OPS,
    methods.MODEM_OPS,
    methods.FREQUENCY_OPS,
    methods.RECEIVER_OPS,
    methods.TRANSMIT_OPS,
    methods.RIG_OPS,
    methods.TEXT_OPS,
    methods.SPOT_OPS,
    methods.WEFAX_OPS,
    methods.NAVTEX_OPS,
    methods.FLMSG_OPS,
    methods.IO_OPS,
    methods.LEGACY_OPS,
]


def test_all_opmaps_registers_every_map():
    assert list(methods.ALL_OPMAPS.values()) == ALL_MAPS


def test_resolve_known_and_unknown():
    assert resolve(methods.MODEM_OPS, "set") == ("modem.set_by_name", "s")
    with pytest.raises(UnknownOperation):
        resolve(methods.MODEM_OPS, "does_not_exist")


def test_all_map_entries_well_formed():
    for opmap in ALL_MAPS:
        for op, (method, kind) in opmap.items():
            assert isinstance(op, str) and op
            assert isinstance(method, str) and "." in method
            assert kind in VALID_KINDS, f"{op} has bad kind {kind!r}"


def test_coerce_types():
    # Doubles vs ints matter to fldigi (the bug that prompted this).
    out = coerce("d", 25)
    assert out == (25.0,) and isinstance(out[0], float)
    out = coerce("i", 3.0)
    assert out == (3,) and isinstance(out[0], int)
    assert coerce("b", "true") == (True,)
    assert coerce("b", "off") == (False,)
    assert coerce("b", 1) == (True,)
    assert coerce("s", 123) == ("123",)
    # An array parameter is ONE XML-RPC array, not spread positionals (fldigi
    # answers "type error" to rig.set_modes("USB", "LSB"); verified 4.2.13).
    assert coerce("A", [1, 2]) == ([1, 2],)
    assert coerce("A", "USB") == (["USB"],)
    assert coerce("ii", [0, 10]) == (0, 10)
    assert coerce("si", ["/tmp/x.png", 5]) == ("/tmp/x.png", 5)
    import xmlrpc.client

    (b,) = coerce("6", "abc")
    assert isinstance(b, xmlrpc.client.Binary) and b.data == b"abc"
    with pytest.raises(ValueError):
        coerce("ii", [1])
    assert coerce(None, None) == ()


def test_keying_methods_are_gated_set():
    # Every keying method must actually appear in a map (so the gate is reachable).
    mapped = {m for opmap in ALL_MAPS for (m, _a) in opmap.values()}
    for keyer in ("main.tx", "main.tune", "main.run_macro"):
        assert keyer in mapped
    # send_file / send_message live in the fax map
    assert "wefax.send_file" in mapped
    assert "navtex.send_message" in mapped
    assert KEYING_METHODS  # non-empty


def test_log_fields():
    # Every settable field is also gettable, except contest_counter, which fldigi
    # exposes as a setter only (log.set_contest_counter, no getter).
    for field in methods.LOG_SET_FIELDS:
        if field != "contest_counter":
            assert field in methods.LOG_GET_FIELDS


def test_no_duplicate_methods_within_a_map():
    for opmap in ALL_MAPS:
        seen = [m for (m, _a) in opmap.values()]
        assert len(seen) == len(set(seen)), "duplicate method within a single group"
