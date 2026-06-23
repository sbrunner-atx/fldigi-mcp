# Installation & Safety Model

This document describes how `fldigi-mcp` is installed and how its transmit
safety works. It is written for a semi-technical audience and is the reference
for the packaged desktop-extension (`.mcpb`) behavior.

## Design goals

- **Out-of-the-box.** A normal install asks for one thing — your callsign — and
  everything else has a sensible default.
- **Safe by default.** Nothing can put your station on the air unless you have
  identified yourself with a callsign. Reading and tuning the software is always
  safe.
- **Changeable later.** Every setting can be edited at any time from the
  connector's settings page; nothing is locked in at install.

## Packaging

The server is distributed as an MCP Bundle (`.mcpb`) using the `uv` server type.
This means:

- Dependencies are declared in `pyproject.toml` and resolved by the host app.
- No bundled Python and **no separate Python install required** by the user.
- One file, one click to install. Works on macOS, Windows, and Linux
  (including Raspberry Pi).

## Installation experience

The installer presents a short settings form. Only the callsign is worth
touching; the rest can be left at their defaults.

| Setting | Type | Default | Notes |
| --- | --- | --- | --- |
| **Callsign** | text | _(empty)_ | The only field most users set. It is the single transmit gate — enter it to enable transmit, leave it blank to stay receive-only. |
| **fldigi host** | text | `127.0.0.1` | Change only if fldigi runs on another computer. |
| **fldigi port** | number | `7362` | fldigi's XML-RPC port. |

All settings are editable afterwards from the connector's settings page. The
callsign field carries an inline note explaining that it enables transmit.

## Transmit safety — how it actually works

Transmit safety is enforced in **two layers**. The important one is the first,
because it cannot be bypassed from the user interface.

### Layer 1 — Server-enforced gate (cannot be bypassed)

The **callsign is the single transmit gate.** The server refuses to transmit
unless a callsign is configured. Any non-blank value is accepted — club, event,
vanity, portable (e.g. `W1/AE5VG`), and international calls all work; no format
is enforced.

If the callsign is blank, `send_message` and `tune` return a clear error and the
radio is never keyed — regardless of what the Tool permissions page says.
`receive` and `abort` are always allowed, because they take the station *off*
the air. Read and control tools (status, frequency, modem, received text) are
always available.

The practical result, matching the intended model:

- **No callsign → transmit is blocked.** Hard stop at the server. This also
  covers the non-ham case: someone with no callsign to enter cannot key the
  radio even by accident, even if they set the tool to "Always Allow."
- **Callsign entered → transmit is available,** and each on-air action still
  asks for approval (Layer 2) until the user chooses otherwise.

### Layer 2 — Client approval prompts (Claude Desktop)

Claude Desktop has its own per-tool permission page (Allow / Ask / Block). A
server cannot set or change those labels — they are the user's control. To steer
the client toward safe defaults, `fldigi-mcp` tags its tools with standard MCP
annotations:

- Read/status/control tools are marked **read-only** → safe to allow.
- `send_message` and `tune` are marked **destructive** → clients that honor
  annotations prompt for approval ("Needs Approval") before each use.

Users can still tighten this further by setting the transmit tools to "Ask" or
"Block" on the permissions page. Nothing the user does there can *loosen* Layer 1.

## Remote / distributed stations

fldigi does not have to run on the same machine. Set **fldigi host** (and port if
needed) to point at the machine running fldigi. That machine must launch fldigi
with `--xmlrpc-server-address 0.0.0.0` so it accepts connections, and the link
should be kept on a trusted LAN or tunneled over SSH (the XML-RPC interface is
unauthenticated).

## Underlying settings (for advanced users / developers)

The settings form maps to these environment variables, so the same behavior is
available when running the server manually (e.g. in `claude_desktop_config.json`
during development):

| Setting | Environment variable | Default |
| --- | --- | --- |
| Callsign | `FLDIGI_CALLSIGN` | _(empty)_ |
| fldigi host | `FLDIGI_HOST` | `127.0.0.1` |
| fldigi port | `FLDIGI_PORT` | `7362` |
