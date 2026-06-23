"""Operation maps for the grouped MCP tools, plus a resolver and type coercion.

Each functional group maps a friendly *operation* name to a tuple of
``(xmlrpc_method, kind)`` where ``kind`` is the XML-RPC argument type the method
expects — and also encodes the arity:

* ``None`` — no value argument
* ``"i"``  — one integer argument
* ``"d"``  — one double (float) argument
* ``"b"``  — one boolean argument
* ``"s"``  — one string argument
* ``"A"``  — a list/array argument

The ``kind`` matters: fldigi rejects a call with "type error" if, say, a double
parameter (`set_squelch_level`, `set_frequency`) is sent an integer. ``coerce``
converts the incoming value to the right type before the call.

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
VALID_KINDS = (None, "i", "d", "b", "s", "A")


class UnknownOperation(ValueError):
    """Raised when a group tool is given an operation it does not support."""


def resolve(opmap: dict, operation: str) -> tuple[str, object]:
    """Return ``(method, kind)`` for an operation, or raise UnknownOperation."""
    spec = opmap.get(operation)
    if spec is None:
        valid = ", ".join(sorted(opmap))
        raise UnknownOperation(f"Unknown operation '{operation}'. Valid operations: {valid}")
    return spec


def coerce(kind: object, value) -> tuple:
    """Coerce ``value`` to the XML-RPC type ``kind`` expects; return call params."""
    if kind is None:
        return ()
    if value is None:
        raise ValueError("this operation requires a value.")
    if kind == "A":
        return tuple(value) if isinstance(value, list) else (value,)
    if kind == "i":
        return (int(value),)
    if kind == "d":
        return (float(value),)
    if kind == "b":
        if isinstance(value, str):
            return (value.strip().lower() in _TRUE,)
        return (bool(value),)
    return (str(value),)  # kind == "s"


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
    "take_control": ("rig.take_control", None),
    "release_control": ("rig.release_control", None),
}

TEXT_OPS = {
    "rx_length": ("text.get_rx_length", None),
    "clear_rx": ("text.clear_rx", None),
    "add_tx": ("text.add_tx", "s"),
    "add_tx_queue": ("text.add_tx_queu", "s"),  # fldigi spells it "queu"
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
    "send_file": ("wefax.send_file", "A"),
}

NAVTEX_OPS = {
    "get_message": ("navtex.get_message", "i"),
    "send_message": ("navtex.send_message", "s"),
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
)
