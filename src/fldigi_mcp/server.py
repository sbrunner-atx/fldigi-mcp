"""fldigi-mcp: an MCP server exposing fldigi's full control interface as tools.

The tools are organised into logical **groups** (one permission each) rather than
one tool per XML-RPC method. Each group tool takes an ``operation`` argument, so
e.g. "change the mode" is a single permission regardless of which underlying
method runs. Every method of the supported fldigi release (4.2.13, catalog in
``data/fldigi_methods.json``) is reachable through a named operation, which
``tests/test_coverage.py`` enforces; the ``fldigi_call`` escape hatch remains for
methods a newer build may add.

Safety: the **callsign is the single transmit gate**. Any operation that keys the
transmitter — through the ``transmit``/``fax`` tools or the raw ``fldigi_call``
escape hatch — is refused unless a callsign is configured. Read and control
operations are always available.

Band Guidance (experimental, off by default) enriches frequency/modem changes
with advisory suggestions; it never blocks or changes anything on its own.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from fldigi_mcp import diag, hunt, methods
from fldigi_mcp.bandplan import BandPlan, mode_category
from fldigi_mcp.client import Fldigi, _is_loopback
from fldigi_mcp.config import Config
from fldigi_mcp.methods import KEYING_METHODS, resolve
from fldigi_mcp.process import FldigiProcess

config = Config.from_env()

mcp = FastMCP("fldigi-mcp")

_fldigi = Fldigi(config.host, config.port)
_process = FldigiProcess(config.host, config.port, os.environ.get("FLDIGI_PATH"))

try:
    _bandplan: BandPlan | None = BandPlan(config.region)
except Exception:  # pragma: no cover - data-load safety net
    _bandplan = None


class TransmitNotAllowed(RuntimeError):
    """Raised when a transmit operation is attempted without a configured callsign."""


def _require_transmit_allowed() -> None:
    if not config.callsign:
        raise TransmitNotAllowed(
            "No callsign is configured, so this station is receive-only. Add your "
            "callsign in the fldigi server settings to enable transmit — a station "
            "must identify on the air. Leave it blank to stay receive-only."
        )


def _run(opmap: dict, operation: str, value: Any = None, gate: bool = False):
    """Resolve an operation to a method, coerce the value to the expected XML-RPC
    type, and invoke it — enforcing the transmit gate for keying methods."""
    method, kind = resolve(opmap, operation)
    if gate and method in KEYING_METHODS:
        _require_transmit_allowed()
    params = methods.coerce(kind, value)
    return _fldigi.call(method, *params)


# --- Status (read) -----------------------------------------------------------


@mcp.tool()
def status() -> dict:
    """Snapshot: version, modem, frequency (Hz), TX/RX state, transmit gate, region, band."""
    freq = _fldigi.frequency()
    snapshot = {
        "version": _fldigi.version(),
        "modem": _fldigi.modem_name(),
        "frequency_hz": freq,
        "trx_state": _fldigi.trx_status(),
        "callsign": config.callsign or None,
        "transmit_ready": config.transmit_ready,
        "band_guidance": config.band_guidance,
        "region": config.region,
    }
    if _bandplan is not None:
        snapshot["band"] = _bandplan.band_for(freq)
    return snapshot


# --- Diagnostics (read, no fldigi connection) --------------------------------


@mcp.tool()
def diagnostics() -> dict:
    """Host + network diagnostics for troubleshooting connectivity.

    Does NOT connect to fldigi. Reports the resolved FLDIGI_HOST/PORT, this
    process's Python and hostname, the transmit-gate state, and the host's
    network interfaces — so you can tell whether the process can even see the
    target's network (e.g. when running host-side vs. sandboxed). If a non-
    loopback host times out, see mcp-host-bridge (docs/INSTALL.md).
    """
    net = diag.network_interfaces()
    return {
        "fldigi_host": config.host,
        "fldigi_port": config.port,
        "resolved_target": f"{config.host}:{config.port}",
        "host_is_loopback": _is_loopback(config.host),
        "callsign": config.callsign or None,
        "transmit_ready": config.transmit_ready,
        "band_guidance": config.band_guidance,
        "region": config.region,
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "hostname": net["hostname"],
        "fqdn": net["fqdn"],
        "primary_outbound_ip": net["primary_outbound_ip"],
        "interface_command": net["interface_command"],
        "ipv4_addresses": net["ipv4_addresses"],
        "interfaces_raw": net["interfaces_raw"],
    }


# --- Grouped tools -----------------------------------------------------------


@mcp.tool()
def application(operation: str, save_log: bool = False, save_macros: bool = False) -> dict:
    """The fldigi program and its process.

    Info operations: version, version_struct, name, name_version, config_dir, list_methods.
    Process operations: launch, stop, terminate, is_running.

    `launch` starts fldigi pointed at the configured XML-RPC endpoint; `stop`/
    `terminate` ask it to quit (saving options; optionally the log/macros) and
    fall back to ending a process this server started.
    """
    if operation in methods.STATION_OPS:
        return {"operation": operation, "result": _run(methods.STATION_OPS, operation)}
    if operation == "is_running":
        return {"operation": operation, "result": _process.is_running()}
    if operation == "launch":
        return {"operation": operation, "result": _process.launch()}
    if operation in ("stop", "terminate"):
        mask = 1 | (2 if save_log else 0) | (4 if save_macros else 0)
        return {"operation": operation, "result": _process.stop(save_bitmask=mask)}
    raise ValueError(
        "operation must be one of: version, version_struct, name, name_version, "
        "config_dir, list_methods, launch, stop, terminate, is_running"
    )


@mcp.tool()
def modem(operation: str, value: Any = None) -> dict:
    """Operating mode (the fldigi "Op Mode" menu) and modem settings.
    operations: get, list, get_id, get_max_id, set (value=mode name e.g. 'BPSK31'),
    set_by_id (value=id), get_io_names (modems usable for KISS/ARQ I/O),
    get/set/inc_carrier, get/set/inc_afc_range, get/set/inc_bandwidth, get_quality,
    search_up, search_down, olivia_get/set_bandwidth, olivia_get/set_tones.
    """
    result = _run(methods.MODEM_OPS, operation, value)
    out = {"operation": operation, "result": result}
    if operation in ("set", "set_by_id") and config.band_guidance and _bandplan is not None:
        suggestion = _bandplan.watering_hole_suggestion(_fldigi.modem_name(), _fldigi.frequency())
        if suggestion:
            out["guidance"] = suggestion
    return out


@mcp.tool()
def frequency(operation: str, value: Any = None) -> dict:
    """RF frequency and waterfall sideband. operations: get, set (value=Hz),
    increment (value=Hz), get_sideband, set_sideband (value='USB'|'LSB').
    """
    previous = _fldigi.frequency() if operation == "set" else None
    result = _run(methods.FREQUENCY_OPS, operation, value)
    out = {"operation": operation, "result": result}
    if (
        operation == "set"
        and config.band_guidance
        and _bandplan is not None
        and previous is not None
    ):
        current = _fldigi.frequency()
        modem_name = _fldigi.modem_name()
        guidance = []
        warning = _bandplan.band_plan_warning(current, mode_category(modem_name))
        if warning:
            guidance.append(warning)
        if _bandplan.band_for(previous) != _bandplan.band_for(current):
            suggestion = _bandplan.watering_hole_suggestion(modem_name, current)
            if suggestion:
                guidance.append(suggestion)
        if guidance:
            out["guidance"] = guidance
    return out


@mcp.tool()
def controls(operation: str, value: Any = None) -> dict:
    """fldigi operating controls (the AFC / SQL / Rev / Lock / RxID / TxID buttons) and status.
    operations: get/set/toggle_afc, get/set/toggle_squelch (SQL),
    get/set/inc_squelch_level, get/set/toggle_reverse (Rev), get/set/toggle_lock (Lock),
    get/set/toggle_rxid (RxID), get/set/toggle_txid (TxID), get_status1, get_status2,
    get_trx_status, get_trx_state.
    """
    return {"operation": operation, "result": _run(methods.RECEIVER_OPS, operation, value)}


def _send_message(text: str, return_to_rx: bool) -> dict:
    _require_transmit_allowed()
    _fldigi.call("text.clear_tx")
    _fldigi.call("text.add_tx", text + "^r" if return_to_rx else text)
    _fldigi.call("main.tx")
    return {
        "operation": "send",
        "state": "transmitting",
        "callsign": config.callsign,
        "text": text,
        "auto_return_to_rx": return_to_rx,
    }


@mcp.tool()
def transmit(
    operation: str,
    value: Any = None,
    text: str | None = None,
    return_to_rx: bool = True,
) -> dict:
    """Transmitter control. operations: tx, tune, rx, abort, disable_tx, enable_tx,
    run_macro (value=id), get_max_macro_id, send (text=...), and timing information:
    tx_timing (value=test string), char_rates, char_timing (value=one character); both
    timings return 'samples : sample rate : seconds'.

    Keying operations (tx, tune, run_macro, send) require a configured callsign;
    rx, abort, disable_tx and the timing operations never key and are always allowed.
    `send` queues text and transmits, auto-returning to receive by default.
    """
    if operation == "send":
        return _send_message(text or "", return_to_rx)
    return {
        "operation": operation,
        "result": _run(methods.TRANSMIT_OPS, operation, value, gate=True),
    }


@mcp.tool()
def rig(operation: str, value: Any = None) -> dict:
    """Rig (CAT) control via flrig/Hamlib/RigCAT. operations: get/set_name,
    get/set_frequency (value=Hz), get/set_mode (value=name), get_modes,
    set_modes (value=[...]), get/set_bandwidth, get_bandwidths,
    set_bandwidths (value=[...]), get/set_notch, enable_qsy (value=1|0),
    set_smeter / set_pwrmeter (value=int, drives fldigi's meter display).
    """
    return {"operation": operation, "result": _run(methods.RIG_OPS, operation, value)}


@mcp.tool()
def log(operation: str, field: str | None = None, value: str | None = None) -> dict:
    """Logbook (QSO / contest) fields. operations: get (field=...), set (field=..., value=...),
    clear, last_record, all_records.

    Settable fields: call, name, qth, locator, serial_number, exchange, rst_in, rst_out,
    contest_counter (set only: the starting contest serial number).
    Gettable fields also include frequency, time_on/off, serial_number_sent, state,
    province, country, band, notes, az. last_record / all_records return ADIF.
    """
    if operation in ("last_record", "all_records"):
        return {"operation": operation, "result": _fldigi.call(f"logbook.{operation}")}
    if operation == "clear":
        return {"operation": "clear", "result": _fldigi.call("log.clear")}
    if operation == "get":
        if field not in methods.LOG_GET_FIELDS:
            raise ValueError(
                f"Unknown log field '{field}'. Valid: {', '.join(methods.LOG_GET_FIELDS)}"
            )
        return {"operation": "get", "field": field, "result": _fldigi.call(f"log.get_{field}")}
    if operation == "set":
        if field not in methods.LOG_SET_FIELDS:
            raise ValueError(
                f"Field '{field}' is not settable. Settable: {', '.join(methods.LOG_SET_FIELDS)}"
            )
        if value is None:
            raise ValueError("set requires a value.")
        return {
            "operation": "set",
            "field": field,
            "result": _fldigi.call(f"log.set_{field}", value),
        }
    raise ValueError("operation must be one of: get, set, clear")


@mcp.tool()
def text(operation: str, value: Any = None, start: int = 0, length: int | None = None) -> dict:
    """RX/TX text and data. operations: read (decoded RX text; start/length),
    rx_length, get_rx (value=[start, length], the raw byte range), clear_rx,
    add_tx (value=text), add_tx_queue, add_tx_bytes (value=text or bytes), clear_tx,
    get_rxtx_data, get_rx_data, get_tx_data.

    `add_tx` / `add_tx_bytes` only stage text in the TX widget; they do not transmit.
    """
    if operation == "read":
        return {"operation": "read", "result": _fldigi.read_rx(start, length)}
    return {"operation": operation, "result": _run(methods.TEXT_OPS, operation, value)}


@mcp.tool()
def spot(operation: str, value: Any = None) -> dict:
    """Spotting / PSK Reporter. operations: get_auto, set_auto (value=bool),
    toggle_auto, pskrep_count.
    """
    return {"operation": operation, "result": _run(methods.SPOT_OPS, operation, value)}


@mcp.tool()
def wefax(operation: str, value: Any = None) -> dict:
    """WEFAX (weather fax) mode. operations: state, skip_apt, skip_phasing, tx_abort,
    end_reception, start_manual_reception, set_adif_log (value=bool),
    set_max_lines (value=int), get_received_file (value=timeout),
    send_file (value=[filename, timeout_seconds]).

    send_file transmits and is callsign-gated.
    """
    return {"operation": operation, "result": _run(methods.WEFAX_OPS, operation, value, gate=True)}


@mcp.tool()
def navtex(operation: str, value: Any = None) -> dict:
    """NAVTEX / SitorB mode. operations: get_message (value=timeout seconds),
    send_message (value=text).

    send_message transmits and is callsign-gated.
    """
    return {"operation": operation, "result": _run(methods.NAVTEX_OPS, operation, value, gate=True)}


@mcp.tool()
def flmsg(operation: str) -> dict:
    """flmsg (message forms) interworking. operations: online, available, transfer,
    squelch, get_data (RX data since the last query).

    These signal or hand data to a running flmsg; none of them key the transmitter.
    """
    return {"operation": operation, "result": _run(methods.FLMSG_OPS, operation)}


@mcp.tool()
def io(operation: str) -> dict:
    """ARQ / KISS I/O port. operations: in_use (which port is active), enable_kiss,
    enable_arq.
    """
    return {"operation": operation, "result": _run(methods.IO_OPS, operation)}


@mcp.tool()
def legacy(operation: str, value: Any = None) -> dict:
    """Deprecated fldigi methods, kept so the whole catalog is reachable. Each has a
    current equivalent, which you should prefer:
    get/set_sideband -> frequency get/set_sideband; rsid -> controls toggle_rxid;
    get/set_rig_name, get/set_rig_frequency, get/set_rig_mode(s), get/set_rig_bandwidth(s)
    -> the rig tool; log_get_sideband -> frequency get_sideband;
    flmsg_online/available/transfer/squelch -> the flmsg tool.
    """
    return {"operation": operation, "result": _run(methods.LEGACY_OPS, operation, value)}


_CAPS: dict = {"key": None, "at": 0.0, "names": frozenset()}
_CAPS_TTL = 30.0


def _has_method(name: str) -> bool:
    """Is this fldigi serving `name`? Capability detection, never version detection: the
    patched methods appear in fldigi.list only on a build that carries the patch, and a
    merged release would carry them too. The answer is cached per connection for
    _CAPS_TTL seconds (fldigi.list is 18 kB) and dropped on any error, so swapping the
    fldigi under a running server is picked up within half a minute."""
    import time

    key = (_fldigi.host, _fldigi.port)
    now = time.time()
    if _CAPS["key"] != key or now - _CAPS["at"] > _CAPS_TTL:
        try:
            names = frozenset(m["name"] for m in _fldigi.call("fldigi.list"))
        except Exception:
            _CAPS.update(key=None, at=0.0, names=frozenset())
            return False
        _CAPS.update(key=key, at=now, names=names)
    return name in _CAPS["names"]


_BROWSER_HINT = (
    "This fldigi has no browser.* methods. They come from the Signal Browser XML-RPC "
    "patch shipped in fldigi-mcp (patches/fldigi-4.2.13-browser-xmlrpc.patch; prepared for "
    "upstream submission). Build fldigi with it, or use signal_hunt with the audio tap instead."
)


def _browser_available() -> bool:
    return _has_method("browser.get_channels")


@mcp.tool()
def browser(operation: str = "channels") -> dict:
    """fldigi's Signal Browser over XML-RPC: every station the multi-channel decoder
    bank has locked to in the passband, with the text decoded on each channel. This is
    what the left-hand browser panel shows, and it copies stations far too weak for
    the waterfall to show. operations: channels (list of {channel, freq, active, text};
    text accumulates since the last clear, a newline marks a lost-and-regained signal),
    clear, available.

    Runs for PSK, RTTY and CW modems (fldigi's browser covers those). Needs a fldigi
    built with the patch in fldigi-mcp/patches; stock 4.2.13 has no browser.* methods,
    and then this tool says so instead of failing. Receive only.
    """
    if operation == "available":
        return {"available": _browser_available()}
    if not _browser_available():
        return {"operation": operation, "available": False, "hint": _BROWSER_HINT}
    return {
        "operation": operation,
        "modem": _fldigi.call("modem.get_name"),
        "result": _run(methods.BROWSER_OPS, operation),
    }


_RSID_HINT = (
    "This fldigi has no rsid.* methods. They come from patches/fldigi-4.2.13-rsid-hits.patch "
    "in fldigi-mcp (applies on top of the browser patch). Without it, RSID only switches "
    "the modem; use `controls` toggle_rxid and read the modem name."
)


@mcp.tool()
def rsid(operation: str = "hits") -> dict:
    """RSID bursts the detector heard: which modes were announced in the passband and
    where, as {utc, mode, hz} entries since the last clear. Works with fldigi's RSID set
    to notify-only (RxID on, "do not change modem"), so the current modem keeps decoding
    while the list tells you what else is on. operations: hits, clear, available.

    Needs a fldigi built with the rsid-hits patch in fldigi-mcp/patches; on stock 4.2.13
    the tool says so instead of failing. Receive only.
    """
    ok = _has_method("rsid.get_hits")
    if operation == "available":
        return {"available": ok}
    if not ok:
        return {"operation": operation, "available": False, "hint": _RSID_HINT}
    return {"operation": operation, "result": _run(methods.RSID_OPS, operation)}


@mcp.tool()
def fldigi_call(method: str, params: list | None = None) -> dict:
    """Escape hatch: call ANY fldigi XML-RPC method by dotted name (e.g. 'rig.get_mode').

    Use `station` with operation 'list_methods' to discover every method the
    running build supports. Keying methods remain callsign-gated.
    """
    if method in KEYING_METHODS:
        _require_transmit_allowed()
    args = tuple(params) if params else ()
    return {"method": method, "result": _fldigi.call(method, *args)}


# --- Signal hunt (experimental) ----------------------------------------------

_SILENCE_WARNING = (
    "audio is all zeros. Either the input device is silent or this process has no microphone "
    "permission (macOS: System Settings > Privacy & Security > Microphone, allow Claude). If the "
    "server does not run where the audio is, run fldigi-mcp-tap beside fldigi and set "
    "FLDIGI_HUNT_URL."
)


@mcp.tool()
def signal_hunt(
    seconds: float = 20.0,
    mode: str | None = None,
    device: str | None = None,
    wav: str | None = None,
    method: str = "audio",
    top: int = 4,
) -> dict:
    """Find and name the signals in the receiver audio and rank them the way a contest
    operator reads the waterfall: the station that sits still and calls CQ scores highest.

    method 'audio' (default): tap `seconds` of audio from the input device (FLDIGI_AUDIO_DEVICE,
    the device fldigi listens on; or `device` as a name substring or index; `wav` analyses a
    file instead). Needs the optional extra: pip install 'fldigi-mcp[hunt]'.
    method 'devices': list the input devices the tap can open.
    method 'browser': read fldigi's Signal Browser (needs the browser patch, see the
    `browser` tool): one candidate per channel the decoder bank holds, with its text,
    for the current modem family (PSK, RTTY or CW). Finds stations the spectrum
    analyser ranks near the floor, but names no mode: it reports what fldigi is set to.
    method 'api': blind fallback with no audio access; steps modem.search_up across the
    passband for each modem (mode='RTTY,BPSK31,...') and reads modem.get_quality. Slow.

    Each candidate carries carrier_hz, mode (RTTY with shift, CW, BPSK31/63/125, Olivia
    with tones and bw, MFSK16, DominoEX, MT63, or unknown), db_over_floor, persistence
    (fraction of the window it was present), periodicity (a CQ loop repeats), score, and
    fldigi_modem, the name tune_to needs. Nothing here transmits.
    """
    if method == "devices":
        return {"devices": hunt.list_devices()}
    if method == "browser":
        if not _browser_available():
            return {"method": "browser", "candidates": [], "warning": _BROWSER_HINT}
        modem_name = _fldigi.call("modem.get_name")
        chans = _fldigi.call("browser.get_channels")
        cands = []
        for c in chans:
            txt = c.get("text", "")
            cands.append(
                {
                    "carrier_hz": c["freq"],
                    "mode": modem_name,
                    "fldigi_modem": modem_name,
                    "channel": c["channel"],
                    "active": bool(c.get("active")),
                    "chars": len(txt),
                    "text_tail": txt[-80:],
                    "cq": " CQ " in f" {txt.upper()} ",
                    "confidence": "high" if len(txt.strip()) >= 12 else "low",
                }
            )
        cands.sort(key=lambda c: (c["cq"], c["active"], c["chars"]), reverse=True)
        return {
            "method": "browser",
            "source": f"fldigi Signal Browser, modem {modem_name}",
            "candidates": cands[: max(1, top)],
            "note": "Mode is what fldigi is set to, not measured. tune_to a candidate's "
            "carrier_hz with the same modem to read it in the main window.",
        }
    if method == "api":
        modems = [m.strip() for m in (mode or "RTTY,BPSK31").split(",") if m.strip()]
        return {"method": "api", "candidates": hunt.api_hunt(_fldigi, modems)}
    if wav:
        x, fs = hunt.read_wav(wav)
        source = wav
    elif config.hunt_url:
        # the audio is elsewhere (sandbox, remote fldigi): ask the host-side fldigi-mcp-tap
        import urllib.request

        url = f"{config.hunt_url}/hunt?seconds={float(seconds)}&top={max(1, top)}"
        with urllib.request.urlopen(url, timeout=seconds + 30) as r:
            out = json.loads(r.read().decode())
        out["method"] = "tap"
        out["source"] = f"{config.hunt_url} ({out.get('source')})"
        if mode:
            want = mode.upper()
            out["candidates"] = [
                c
                for c in out["candidates"]
                if c["mode"].upper().startswith(want)
                or want in (c.get("fldigi_modem") or "").upper()
            ]
        return out
    else:
        dev = device or config.audio_device or None
        x, fs = hunt.capture(seconds, dev)
        source = f"device {dev or 'default'}"
        if float((x**2).mean()) == 0.0:
            return {
                "method": "audio",
                "source": source,
                "seconds": seconds,
                "candidates": [],
                "warning": _SILENCE_WARNING,
            }
    cands = hunt.analyse(x, fs, top=max(1, top))
    if mode:
        want = mode.upper()
        cands = [
            c
            for c in cands
            if c["mode"].upper().startswith(want) or want in (c.get("fldigi_modem") or "").upper()
        ]
    return {
        "method": "audio",
        "source": source,
        "seconds": round(len(x) / fs, 1),
        "candidates": cands,
        "note": "Contestia shares Olivia's grid and THOR shares DominoEX's; only RSID separates "
        "them. Confirm a candidate by tuning to it and reading 20 s of text.",
    }


@mcp.tool()
def tune_to(carrier_hz: int, fldigi_modem: str, rxid: bool = False, afc: bool = True) -> dict:
    """Set fldigi to a signal_hunt candidate: modem by fldigi name (e.g. 'RTTY', 'BPSK31',
    'OLIVIA-8/250', 'MFSK16', 'DOMEX11', 'MT63-500'), the audio carrier, AFC on, and RxID
    off by default so another station's RSID burst cannot retune the modem mid-pass.
    Read the result with `text` read after 20 seconds; `modem` get_quality says whether
    it locked. Does not transmit.
    """
    previous = _fldigi.call("modem.get_name")
    _fldigi.call("main.set_rsid", bool(rxid))
    _fldigi.call("modem.set_by_name", fldigi_modem)
    now = _fldigi.call("modem.get_name")
    if now != fldigi_modem:
        raise ValueError(
            f"fldigi does not know modem {fldigi_modem!r} (still {now!r}); see modem list"
        )
    _fldigi.call("modem.set_carrier", int(carrier_hz))
    _fldigi.call("main.set_afc", bool(afc))
    return {
        "previous_modem": previous,
        "modem": now,
        "carrier_hz": _fldigi.call("modem.get_carrier"),
        "afc": afc,
        "rxid": rxid,
        "frequency_hz": _fldigi.frequency(),
    }


# --- Band Guidance (experimental, advisory) ----------------------------------


@mcp.tool()
def band_guidance(
    operation: str,
    frequency_hz: float | None = None,
    mode: str | None = None,
    band: str | None = None,
) -> dict:
    """Advisory band guidance (experimental, region-aware) — informational / QSY help only.

    operations:
      - lookup (frequency_hz, optional mode): what the band plan says at a frequency.
      - watering_hole (mode, optional band): the preferred calling frequency for a mode.
      - move_to_watering_hole (mode): set the dial to that frequency (does NOT transmit).
    """
    if _bandplan is None:
        return {"available": False}
    if operation == "lookup":
        if frequency_hz is None:
            raise ValueError("lookup requires frequency_hz.")
        category = mode_category(mode) if mode else "DATA"
        return {
            "region": config.region,
            "query_mode": mode,
            "category": category,
            "result": _bandplan.segment_check(frequency_hz, category),
        }
    if operation == "watering_hole":
        if not mode:
            raise ValueError("watering_hole requires mode.")
        target_band = band or _bandplan.band_for(_fldigi.frequency())
        return {
            "region": config.region,
            "mode": mode,
            "band": target_band,
            "frequency_hz": _bandplan.watering_hole(mode, target_band),
        }
    if operation == "move_to_watering_hole":
        if not mode:
            raise ValueError("move_to_watering_hole requires mode.")
        current_band = _bandplan.band_for(_fldigi.frequency())
        target = _bandplan.watering_hole(mode, current_band)
        if target is None:
            return {
                "moved": False,
                "reason": (
                    f"No calling frequency for {mode} on {current_band or 'this band'} "
                    f"in Region {config.region}."
                ),
            }
        previous = _fldigi.set_frequency(target)
        return {
            "moved": True,
            "mode": mode,
            "band": current_band,
            "previous_hz": previous,
            "current_hz": _fldigi.frequency(),
        }
    raise ValueError("operation must be one of: lookup, watering_hole, move_to_watering_hole")


def main() -> None:
    """Console-script entry point (wired up in pyproject.toml's [project.scripts])."""
    mcp.run()


if __name__ == "__main__":
    main()
