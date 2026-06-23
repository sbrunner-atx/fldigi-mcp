# fldigi-mcp — Test Plan

A repeatable plan to verify the server end to end, whether running from source or
as the installed `.mcpb` extension. Most tests are read-only or self-restoring;
on-air tests are clearly marked and require a licensed operator.

## Preconditions

- fldigi is running and reachable (XML-RPC on by default at `127.0.0.1:7362`).
- The MCP client (Claude Desktop or the MCP Inspector) shows the fldigi tools.
- For transmit tests: a callsign configured, and **a dummy load or the
  RigBlaster with no antenna** — never test transmit into a live antenna casually.

## Conventions

- **Restore** steps return the station to its prior state.
- Pass = result matches "Expected"; note any deviation.

---

## A. Connectivity & configuration

| ID | Action | Expected |
| --- | --- | --- |
| A1 | `status` | Returns version, modem, frequency_hz, trx_state, callsign, transmit_ready, band_guidance, region, band. |
| A2 | Check `callsign` in A1 | **Matches exactly what you entered** in settings (e.g. `AE5VG`, not `AE%VG`). |
| A3 | `application` version / name_version / config_dir | Correct strings; config_dir is a real path. |
| A4 | `application` list_methods | Array of method structs; length > 150 on fldigi 4.2.x. |

## B. Read operations (per group)

| ID | Action | Expected |
| --- | --- | --- |
| B1 | `modem` get / list / get_id / get_max_id | Current modem name; full modem list; integer ids. |
| B2 | `frequency` get / get_sideband | Frequency in Hz; `USB` or `LSB`. |
| B3 | `controls` get_afc / get_squelch_level / get_rxid / get_txid / get_trx_state | Booleans/levels/`RX`. |
| B4 | `rig` get_mode / get_modes / get_frequency | Mode string; list; Hz (depends on CAT setup). |
| B5 | `log` get (call, name, rst_in) / last_record | Field contents (may be empty); ADIF string. |
| B6 | `text` rx_length / read | Integer; decoded RX text. |
| B7 | `spot` get_auto / pskrep_count | Boolean; integer. |
| B8 | `wefax` state | e.g. `Not in wefax mode`. |

## C. Control writes (with restore) — verifies type coercion

| ID | Action | Expected |
| --- | --- | --- |
| C1 | `controls` set_squelch_level 25, then 30 | Returns the **old** value each time; no "type error" (double coercion works). |
| C2 | `controls` set_afc false, then restore | Boolean setter works; returns old state. |
| C3 | `modem` set "RTTY", then set "BPSK31" | String setter works; restored. |
| C4 | `frequency` set 14070000, then restore | Double setter works; returns old Hz. |
| C5 | `controls` toggle_squelch twice | Toggles and returns; net no change. |

## D. Transmit safety (callsign gate) — ON AIR / dummy load

| ID | Action | Expected |
| --- | --- | --- |
| D1 | With **no callsign** configured: `transmit` send "test" | **Refused** with a clear "receive-only / set callsign" message. Radio never keys. |
| D2 | With callsign set: `transmit` send "V V V de <call>" (return_to_rx=true) | Keys PTT, sends, **auto-returns to RX**. (Watch the interface's PTT LED.) |
| D3 | `transmit` disable_tx, then enable_tx | Both succeed; disable_tx forces receive-only. |
| D4 | `transmit` rx / abort | Always allowed (take station off air). |
| D5 | `fldigi_call` "main.tx" with no callsign | **Refused** by the gate (escape hatch honors the gate). |

## E. Band Guidance (enable the toggle first)

| ID | Action | Expected |
| --- | --- | --- |
| E1 | `band_guidance` watering_hole mode=PSK31 | Region-correct calling frequency (e.g. 20 m → 14.070). |
| E2 | `band_guidance` lookup at an in-segment freq | `in_segment: true`. |
| E3 | `band_guidance` lookup at an out-of-segment freq (e.g. 14.230 with DATA) | `in_segment: false`. |
| E4 | With guidance ON: `modem` set to a mode off its watering hole | Result includes a `guidance` watering-hole suggestion. |
| E5 | With guidance ON: `frequency` set outside the digital segment | Result includes a `guidance` band-plan warning. |
| E6 | `band_guidance` lookup at a non-amateur freq (e.g. 3.0 MHz) | `band: null` / no segment — degrades gracefully, no guess. |
| E7 | Compare a region-specific boundary across `FLDIGI_REGION` 1/2/3 | Segment edges differ as documented. |

## F. Escape hatch & errors

| ID | Action | Expected |
| --- | --- | --- |
| F1 | `fldigi_call` method="modem.get_submode" | Reaches an ungrouped method; returns value. |
| F2 | Any group with an invalid operation | Clear "Unknown operation … valid operations: …" error. |
| F3 | A setter with a missing value | Clear "requires a value" error. |
| F4 | Stop fldigi, then `status` | Friendly "Could not reach fldigi. Is it running?" error. |

## G. Process management (optional, disruptive)

| ID | Action | Expected |
| --- | --- | --- |
| G1 | `application` is_running | Boolean. |
| G2 | `application` launch (when fldigi closed) | Starts fldigi; becomes reachable. |
| G3 | `application` stop | fldigi quits gracefully. |

## H. Automated regression (no radio needed)

Run before every release:

```bash
uv run ruff check .
uv run pytest          # band-plan logic, operation maps, type coercion
```

All green = the pure logic is sound; the live matrix above covers the parts that
need a real fldigi.
