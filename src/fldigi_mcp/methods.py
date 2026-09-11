"""Operation maps for the grouped MCP tools, plus a resolver and type coercion.

Each functional group maps a friendly *operation* name to a tuple of
``(xmlrpc_method, kind)`` where ``kind`` is the XML-RPC argument type the method
expects — and also encodes the arity:

* ``None`` — no value argument
* ``"i"``  — one integer argument
* ``"d"``  — one double (float) argument
* ``"b"``  — one boolean argument
* ``"s"``  — one string argument
* ``"A"``  — ONE array argument (a list is passed as a single XML-RPC array)
* ``"6"``  — one bytes argument (XML-RPC base64; a str is UTF-8 encoded)
* ``"ii"``, ``"si"`` — two positional arguments of those types (value is a list)

The ``kind`` matters: fldigi rejects a call with "type error" if, say, a double
parameter (`set_squelch_level`, `set_frequency`) is sent an integer, or if an
array parameter (`rig.set_modes`) is spread into positional strings. ``coerce``
converts the incoming value to the right shape before the call.

The kind letters are fldigi's own signature letters (``fldigi.list``), so
``tests/test_coverage.py`` can check every entry against the live catalog in
``data/fldigi_methods.json`` and prove that every method of the supported
fldigi release is reachable through a named operation.

Kept as plain data here (separate from ``server.py``) so the whole mapping is
unit-testable without the MCP SDK or a running fldigi.
"""

from __future__ import annotations

KEYING_METHODS = frozenset(
    {
        "main.tx",
        "main.tune",
        "main.run_macro",
        "wefax.send_file",
        "navtex.send_message",
    }
)

_TRUE = {"1", "true", "yes", "on"}
VALID_KINDS = (None, "i", "d", "b", "s", "A", "6", "ii", "si")

# Methods the server, client or process modules call directly rather than
# through an operation map (see tests/test_coverage.py).
DIRECT_METHODS = frozenset(
    {
        "fldigi.name_version",  # client / process liveness
        "fldigi.terminate",  # process.stop
        "text.get_rx",  # client.read_rx
        "text.get_rx_length",
        "text.clear_rx",
        "text.clear_tx",
        "text.add_tx",
        "main.tx",
        "main.rx",
        "main.tune",
        "main.abort",
        "main.get_frequency",
        "main.set_frequency",
        "main.get_trx_status",
        "main.get_status1",
        "main.get_status2",
        "modem.get_name",
        "modem.get_names",
        "modem.set_by_name",
        "modem.get_quality",
        "log.clear",
        "logbook.last_record",
        "logbook.all_records",
    }
)


class UnknownOperation(ValueError):
    """Raised when a group tool is given an operation it does not support."""


def resolve(opmap: dict, operation: str) -> tuple[str, object]:
    """Return ``(method, kind)`` for an operation, or raise UnknownOperation."""
    spec = opmap.get(operation)
    if spec is None:
        valid = ", ".join(sorted(opmap))
        raise UnknownOperation(f"Unknown operation '{operation}'. Valid operations: {valid}")
    return spec


def _one(letter: str, value):
    if letter == "i":
        return int(value)
    if letter == "d":
        return float(value)
    if letter == "b":
        if isinstance(value, str):
            return value.strip().lower() in _TRUE
        return bool(value)
    if letter == "A":
        return list(value) if isinstance(value, (list, tuple)) else [value]
    if letter == "6":
        import xmlrpc.client

        if isinstance(value, xmlrpc.client.Binary):
            return value
        return xmlrpc.client.Binary(
            value if isinstance(value, bytes) else str(value).encode("utf-8")
        )
    return str(value)  # "s"


def coerce(kind: object, value) -> tuple:
    """Coerce ``value`` to the XML-RPC parameter(s) ``kind`` expects; return call params."""
    if kind is None:
        return ()
    if value is None:
        raise ValueError("this operation requires a value.")
    if kind not in VALID_KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    if len(kind) == 1:
        return (_one(kind, value),)
    if not isinstance(value, (list, tuple)) or len(value) != len(kind):
        raise ValueError(
            f"this operation takes {len(kind)} values as a list, e.g. [start, length]."
        )
    return tuple(_one(k, v) for k, v in zip(kind, value, strict=True))


STATION_OPS = {
    "version": ("fldigi.version", None),
    "version_struct": ("fldigi.version_struct", None),
    "name": ("fldigi.name", None),
    "name_version": ("fldigi.name_version", None),
    "config_dir": ("fldigi.config_dir", None),
    "list_methods": ("fldigi.list", None),
}

MODEM_OPS = {
    "get": ("modem.get_name", None),
    "list": ("modem.get_names", None),
    "get_id": ("modem.get_id", None),
    "get_max_id": ("modem.get_max_id", None),
    "get_mode": ("modem.get_mode", None),  # ADIF mode
    "get_submode": ("modem.get_submode", None),  # ADIF submode
    "get_io_names": ("modem.get_io_names", None),  # modems usable for KISS / ARQ I/O
    "set": ("modem.set_by_name", "s"),
    "set_by_id": ("modem.set_by_id", "i"),
    "get_carrier": ("modem.get_carrier", None),
    "set_carrier": ("modem.set_carrier", "i"),
    "inc_carrier": ("modem.inc_carrier", "i"),
    "get_afc_range": ("modem.get_afc_search_range", None),
    "set_afc_range": ("modem.set_afc_search_range", "i"),
    "inc_afc_range": ("modem.inc_afc_search_range", "i"),
    "get_bandwidth": ("modem.get_bandwidth", None),
    "set_bandwidth": ("modem.set_bandwidth", "i"),
    "inc_bandwidth": ("modem.inc_bandwidth", "i"),
    "get_quality": ("modem.get_quality", None),
    "search_up": ("modem.search_up", None),
    "search_down": ("modem.search_down", None),
    "olivia_get_bandwidth": ("modem.olivia.get_bandwidth", None),
    "olivia_set_bandwidth": ("modem.olivia.set_bandwidth", "i"),
    "olivia_get_tones": ("modem.olivia.get_tones", None),
    "olivia_set_tones": ("modem.olivia.set_tones", "i"),
}

FREQUENCY_OPS = {
    "get": ("main.get_frequency", None),
    "set": ("main.set_frequency", "d"),
    "increment": ("main.inc_frequency", "d"),
    "get_sideband": ("main.get_wf_sideband", None),
    "set_sideband": ("main.set_wf_sideband", "s"),
}

RECEIVER_OPS = {
    "get_afc": ("main.get_afc", None),
    "set_afc": ("main.set_afc", "b"),
    "toggle_afc": ("main.toggle_afc", None),
    "get_squelch": ("main.get_squelch", None),
    "set_squelch": ("main.set_squelch", "b"),
    "toggle_squelch": ("main.toggle_squelch", None),
    "get_squelch_level": ("main.get_squelch_level", None),
    "set_squelch_level": ("main.set_squelch_level", "d"),
    "inc_squelch_level": ("main.inc_squelch_level", "d"),
    "get_reverse": ("main.get_reverse", None),
    "set_reverse": ("main.set_reverse", "b"),
    "toggle_reverse": ("main.toggle_reverse", None),
    "get_lock": ("main.get_lock", None),
    "set_lock": ("main.set_lock", "b"),
    "toggle_lock": ("main.toggle_lock", None),
    "get_rxid": ("main.get_rsid", None),
    "set_rxid": ("main.set_rsid", "b"),
    "toggle_rxid": ("main.toggle_rsid", None),
    "get_txid": ("main.get_txid", None),
    "set_txid": ("main.set_txid", "b"),
    "toggle_txid": ("main.toggle_txid", None),
    "get_status1": ("main.get_status1", None),
    "get_status2": ("main.get_status2", None),
    "get_trx_status": ("main.get_trx_status", None),
    "get_trx_state": ("main.get_trx_state", None),
}

TRANSMIT_OPS = {
    "tx": ("main.tx", None),
    "tune": ("main.tune", None),
    "rx": ("main.rx", None),
    "abort": ("main.abort", None),
    "disable_tx": ("main.rx_only", None),  # force receive-only
    "enable_tx": ("main.rx_tx", None),  # restore normal Rx/Tx switching
    "run_macro": ("main.run_macro", "i"),
    "get_max_macro_id": ("main.get_max_macro_id", None),
    # timing information, no keying. fldigi.list declares n:s and n:i for the two
    # timed calls, but the live build rejects strings and ints and accepts a
    # base64 parameter, returning "samples : sample rate : seconds" (verified 4.2.13).
    "tx_timing": ("main.get_tx_timing", "6"),  # value=test string
    "char_rates": ("main.get_char_rates", None),
    "char_timing": ("main.get_char_timing", "6"),  # value=the character
}

RIG_OPS = {
    "get_name": ("rig.get_name", None),
    "set_name": ("rig.set_name", "s"),
    "get_frequency": ("rig.get_frequency", None),
    "set_frequency": ("rig.set_frequency", "d"),
    "get_mode": ("rig.get_mode", None),
    "set_mode": ("rig.set_mode", "s"),
    "get_modes": ("rig.get_modes", None),
    "set_modes": ("rig.set_modes", "A"),
    "get_bandwidth": ("rig.get_bandwidth", None),
    "set_bandwidth": ("rig.set_bandwidth", "s"),
    "get_bandwidths": ("rig.get_bandwidths", None),
    "set_bandwidths": ("rig.set_bandwidths", "A"),
    "get_notch": ("rig.get_notch", None),
    "set_notch": ("rig.set_notch", "i"),
    "enable_qsy": ("rig.enable_qsy", "i"),  # 1/0 enable XML-RPC QSY
    "set_smeter": ("rig.set_smeter", "i"),
    "set_pwrmeter": ("rig.set_pwrmeter", "i"),
    # rig.take_control / rig.release_control were listed here through 0.1.5 but no
    # fldigi 4.2.x build serves them (not in fldigi.list); removed in 0.1.6.
}

TEXT_OPS = {
    "rx_length": ("text.get_rx_length", None),
    "get_rx": ("text.get_rx", "ii"),  # value=[start, length]; raw bytes range
    "clear_rx": ("text.clear_rx", None),
    "add_tx": ("text.add_tx", "s"),
    "add_tx_queue": ("text.add_tx_queu", "s"),  # fldigi spells it "queu"
    "add_tx_bytes": ("text.add_tx_bytes", "6"),  # value=str or bytes
    "clear_tx": ("text.clear_tx", None),
    "get_rxtx_data": ("rxtx.get_data", None),
    "get_rx_data": ("rx.get_data", None),
    "get_tx_data": ("tx.get_data", None),
}

SPOT_OPS = {
    "get_auto": ("spot.get_auto", None),
    "set_auto": ("spot.set_auto", "b"),
    "toggle_auto": ("spot.toggle_auto", None),
    "pskrep_count": ("spot.pskrep.get_count", None),
}

WEFAX_OPS = {
    "state": ("wefax.state_string", None),
    "skip_apt": ("wefax.skip_apt", None),
    "skip_phasing": ("wefax.skip_phasing", None),
    "tx_abort": ("wefax.set_tx_abort_flag", None),
    "end_reception": ("wefax.end_reception", None),
    "start_manual_reception": ("wefax.start_manual_reception", None),
    "set_adif_log": ("wefax.set_adif_log", "b"),
    "set_max_lines": ("wefax.set_max_lines", "i"),
    "get_received_file": ("wefax.get_received_file", "i"),
    "send_file": ("wefax.send_file", "si"),  # value=[filename, timeout]
}

NAVTEX_OPS = {
    "get_message": ("navtex.get_message", "i"),
    "send_message": ("navtex.send_message", "s"),
}

# flmsg (message forms) interworking. flmsg.* is the current namespace; the
# main.flmsg_* aliases are in LEGACY_OPS.
FLMSG_OPS = {
    "online": ("flmsg.online", None),
    "available": ("flmsg.available", None),
    "transfer": ("flmsg.transfer", None),
    "squelch": ("flmsg.squelch", None),
    "get_data": ("flmsg.get_data", None),
}

# ARQ / KISS I/O port selection.
IO_OPS = {
    "in_use": ("io.in_use", None),
    "enable_kiss": ("io.enable_kiss", None),
    "enable_arq": ("io.enable_arq", None),
}

# Deprecated methods fldigi still serves. Kept so the connector covers the whole
# catalog; every one has a current equivalent named in the tool docstring.
LEGACY_OPS = {
    "get_sideband": ("main.get_sideband", None),  # -> frequency get_sideband
    "set_sideband": ("main.set_sideband", "s"),  # -> frequency set_sideband
    "rsid": ("main.rsid", None),  # -> controls toggle_rxid
    "set_rig_name": ("main.set_rig_name", "s"),  # -> rig set_name
    "set_rig_frequency": ("main.set_rig_frequency", "d"),  # -> rig set_frequency
    "set_rig_modes": ("main.set_rig_modes", "A"),  # -> rig set_modes
    "set_rig_mode": ("main.set_rig_mode", "s"),  # -> rig set_mode
    "get_rig_modes": ("main.get_rig_modes", None),  # -> rig get_modes
    "get_rig_mode": ("main.get_rig_mode", None),  # -> rig get_mode
    "set_rig_bandwidths": ("main.set_rig_bandwidths", "A"),  # -> rig set_bandwidths
    "set_rig_bandwidth": ("main.set_rig_bandwidth", "s"),  # -> rig set_bandwidth
    "get_rig_bandwidth": ("main.get_rig_bandwidth", None),  # -> rig get_bandwidth
    "get_rig_bandwidths": (
        "main.get_rig_bandwidths",
        "A",
    ),  # -> rig get_bandwidths (fldigi signature n:A)
    "log_get_sideband": ("log.get_sideband", None),  # -> frequency get_sideband
    "flmsg_online": ("main.flmsg_online", None),  # -> flmsg online
    "flmsg_available": ("main.flmsg_available", None),  # -> flmsg available
    "flmsg_transfer": ("main.flmsg_transfer", None),  # -> flmsg transfer
    "flmsg_squelch": ("main.flmsg_squelch", None),  # -> flmsg squelch
}

# Methods that exist only in a patched fldigi (patches/fldigi-4.2.13-browser-xmlrpc.patch,
# prepared for upstream submission 11 Sep 2026). Kept out of ALL_OPMAPS on purpose: the coverage
# test holds ALL_OPMAPS to the stock 4.2.13 catalog, and the browser tool checks
# fldigi.list before calling these.
BROWSER_OPS = {
    "channels": ("browser.get_channels", None),
    "clear": ("browser.clear", None),
}
PATCHED_OPMAPS = {"browser": BROWSER_OPS}

ALL_OPMAPS = {
    "application": STATION_OPS,
    "modem": MODEM_OPS,
    "frequency": FREQUENCY_OPS,
    "controls": RECEIVER_OPS,
    "transmit": TRANSMIT_OPS,
    "rig": RIG_OPS,
    "text": TEXT_OPS,
    "spot": SPOT_OPS,
    "wefax": WEFAX_OPS,
    "navtex": NAVTEX_OPS,
    "flmsg": FLMSG_OPS,
    "io": IO_OPS,
    "legacy": LEGACY_OPS,
}

# Log fields. Getters exist for all; setters only for these.
LOG_GET_FIELDS = (
    "frequency",
    "time_on",
    "time_off",
    "date_on",
    "date_off",
    "call",
    "name",
    "rst_in",
    "rst_out",
    "serial_number",
    "serial_number_sent",
    "exchange",
    "state",
    "province",
    "country",
    "qth",
    "band",
    "notes",
    "locator",
    "az",
)
LOG_SET_FIELDS = (
    "call",
    "name",
    "qth",
    "locator",
    "serial_number",
    "exchange",
    "rst_in",
    "rst_out",
    "contest_counter",  # set only: starting contest serial number
)
