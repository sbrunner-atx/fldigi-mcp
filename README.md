# fldigi-mcp

<!-- mcp-name: io.github.sbrunner-atx/fldigi-mcp -->

An [MCP](https://modelcontextprotocol.io/) server for controlling
[fldigi](https://www.w1hkj.org/), the popular amateur-radio digital-modem
application, from MCP-aware clients such as Claude Desktop.

fldigi ships a built-in XML-RPC control interface. `fldigi-mcp` connects to it
and exposes the whole API as a small set of logically-grouped MCP tools, so an
assistant can read the radio's state and drive the modem, rig, log, and
transmitter through plain language.

> **Status:** beta. Signal hunting (find, name and tune to a station from the
> receiver audio, 0.2.0) and full API coverage (every one of fldigi's 174 XML-RPC methods
> is reachable through a named operation, enforced by a test), callsign-gated
> transmit, and an optional experimental Band Guidance feature. Supports the
> current fldigi release, **4.2.13**, verified live on 2026-09-09.

## 📻 A field-tested fldigi XML-RPC API reference (free community resource)

Building this server meant mapping fldigi's entire XML-RPC interface and
**verifying every method against a live build** — so we've written it all up and
are sharing it freely, whether or not you ever use this MCP server:

- **[docs/FLDIGI-API.md](docs/FLDIGI-API.md)** — a clean, complete, human-readable
  reference organized by namespace, with transport details, types, worked
  examples, a transmit-safety section, and field-tested gotchas.
- **[docs/FLDIGI-API.pdf](docs/FLDIGI-API.pdf)** — the same, as a printable PDF.
- **[docs/FLDIGI-API-SPEC.md](docs/FLDIGI-API-SPEC.md)** — a terse,
  machine-readable catalog of all **174 methods** (args, return type,
  read/write/keying).

Verified live against **fldigi 4.2.13** via `fldigi.list` on 2026-09-09 (the method
list is identical to 4.2.11, first verified 2026-06-23). It's more complete and
current than the public wiki (it documents methods the wiki omits, e.g. `TxID`,
and flags deprecated ones). **Independent project — not affiliated with the
fldigi / W1HKJ project.** Corrections welcome via
[issues / PRs](https://github.com/sbrunner-atx/fldigi-mcp/issues).

## Highlights

- **Complete control** — every one of the 174 XML-RPC methods in fldigi 4.2.13 is
  reachable through a named operation in one of 17 tools (one permission each);
  `tests/test_coverage.py` fails the build if a method of the shipped catalog is
  not wired or an argument type disagrees with fldigi's signature. The
  `fldigi_call` escape hatch remains for methods a newer build may add.
- **Safe by default** — the **callsign is the single transmit gate**. With no
  callsign configured the station is receive-only; nothing can key the radio.
- **Names match fldigi** — tools and operations mirror fldigi's own API
  namespaces and on-screen labels (Op Mode, AFC, SQL, Rev, Lock, RxID/TxID, T/R).
- **No fragile dependencies** — talks to fldigi with Python's standard-library
  `xmlrpc.client`. The only third-party runtime deps are the MCP SDK and PyYAML
  (for the optional band-plan data).

## Why XML-RPC (and not a third-party library)

fldigi's XML-RPC interface is its official, OS-independent control API. This
project talks to it directly rather than through an unmaintained wrapper,
keeping the moving parts to Python's standard library and fldigi's own API.

## Requirements

To **install the desktop extension** (`.mcpb`) all you need is:

- **fldigi** running (its XML-RPC server is on by default at `127.0.0.1:7362`).

Claude Desktop's `uv` runtime supplies Python and the dependencies, so end users
do **not** install Python or `uv` themselves. (That runtime is currently marked
experimental, so a recent Claude Desktop is recommended.)

For **development from source** you additionally need **Python 3.10+** and
**[uv](https://docs.astral.sh/uv/)** (and **Node.js**, only for the MCP Inspector).

## Install

### Easiest: one-click desktop extension

Download `fldigi-mcp.mcpb` from the latest
[release](https://github.com/sbrunner-atx/fldigi-mcp/releases), then in Claude
Desktop go to **Settings → Extensions → Advanced settings → Install Extension…**
and choose the file.
A short settings form asks for your callsign (everything else has a default).
**No terminal, no Python, no uv to install.**

👉 **New to this? Follow the simple [step-by-step install guide](docs/INSTALL.md).**
Also see the [install & safety model](docs/install-and-safety.md).

### From source (development)

```bash
git clone https://github.com/sbrunner-atx/fldigi-mcp.git
cd fldigi-mcp
uv sync
```

Then add it to Claude Desktop's config
(`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "fldigi": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/fldigi-mcp", "run", "fldigi-mcp"],
      "env": { "FLDIGI_CALLSIGN": "AE5VG" }
    }
  }
}
```

Restart Claude Desktop and ask *"What's fldigi's status?"*. Omit the `env` block
to run receive-only.

### Try it with the MCP Inspector

```bash
uv run mcp dev src/fldigi_mcp/server.py
```

## The Signal Browser patch (`patches/`)

fldigi's Signal Browser, the left-hand panel that decodes up to 30 PSK, RTTY or CW
stations at once, is not on its XML-RPC API. `patches/fldigi-4.2.13-browser-xmlrpc.patch`
touches four files (`psk_browser.h/.cxx`, `viewpsk.cxx`, `xmlrpc.cxx`) and adds two methods, `browser.get_channels` (array of `{channel, freq, active, text}`,
text untrimmed, line breaks kept, accumulated since the last clear) and `browser.clear`. The `browser`
tool and `signal_hunt method="browser"` use them and say so when fldigi is unpatched.
Tested on 4.2.13 (macOS, four synthetic PSK31 stations from 0 to -26 dB: all four
copied in full). The patch applies to the fldigi git HEAD on SourceForge and is prepared
for upstream submission; until it lands, build fldigi from source with it:

```bash
tar xf fldigi-4.2.13.tar.gz && cd fldigi-4.2.13
patch -p1 < /path/to/fldigi-mcp/patches/fldigi-4.2.13-browser-xmlrpc.patch
./configure --prefix=$HOME/.local/fldigi && make -j8 && make install
```

## Tools

Each tool is one permission and takes an `operation` argument, so e.g. "change
the mode" is a single permission regardless of which underlying method runs.

| Tool | Controls (fldigi area) |
| --- | --- |
| `status` | quick snapshot: version, mode, frequency, T/R, callsign, band |
| `diagnostics` | host/network info for connectivity troubleshooting (no fldigi connection) |
| `application` | program info + launch/stop the fldigi process (`fldigi.*`) |
| `modem` | Op Mode / modem select, carrier, bandwidth, AFC range, Olivia |
| `frequency` | dial frequency and waterfall sideband |
| `controls` | AFC, SQL, Rev, Lock, RxID, TxID, status fields |
| `transmit` | T/R, Tune, abort, disable/enable Tx, macros, send — **callsign-gated** |
| `rig` | CAT control: mode, frequency, bandwidth, notch, QSY, meters |
| `log` | Logbook / contest fields; ADIF last/all records |
| `text` | RX/TX text and data streams |
| `spot` | spotting / PSK Reporter |
| `wefax` | WEFAX (weather fax) mode |
| `navtex` | NAVTEX / SitorB mode |
| `flmsg` | flmsg (message forms) interworking |
| `io` | ARQ / KISS I/O port selection |
| `legacy` | deprecated methods fldigi still serves, each with its current equivalent named |
| `band_guidance` | advisory band/watering-hole help (experimental) |
| `signal_hunt` | find and name the signals in the receiver audio; rank CQing stations (experimental, `[hunt]` extra) |
| `tune_to` | set modem and carrier to a `signal_hunt` candidate, receive only |
| `browser` | fldigi's Signal Browser: every station the decoder bank holds, with its text (needs the fldigi patch in `patches/`) |
| `fldigi_call` | escape hatch — call any method by name, incl. future ones |

Use `application` → `list_methods` to enumerate every method the running build
supports. On 4.2.13 all of them are surfaced in a group; `fldigi_call` is for
methods a newer fldigi may add before this connector catches up.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `FLDIGI_HOST` | `127.0.0.1` | fldigi XML-RPC host |
| `FLDIGI_PORT` | `7362` | fldigi XML-RPC port |
| `FLDIGI_CALLSIGN` | _(empty)_ | Operator callsign. **The single transmit gate** — set it to enable transmit; blank keeps the station receive-only |
| `FLDIGI_BAND_GUIDANCE` | `off` | Experimental advisory band guidance. `on` to enable |
| `FLDIGI_REGION` | `2` | IARU region for band guidance: `1`, `2`, or `3` |
| `FLDIGI_PATH` | _(auto)_ | Explicit path to the fldigi executable (for `application launch`) |

In the packaged desktop extension these appear as a settings form — most users
only ever fill in the callsign.

### Transmit safety

The **callsign is the single transmit gate**. Keying operations (`transmit`
tx/tune/run_macro/send, and the `wefax`/`navtex` send operations, and any keying
method via `fldigi_call`) refuse unless `FLDIGI_CALLSIGN` is set. With it blank,
the station is receive-only. `rx`, `abort`, and `disable_tx` are always allowed
because they take the station *off* the air. Any non-blank value is accepted
(club, event, vanity, portable, and international calls all work). See
[docs/install-and-safety.md](docs/install-and-safety.md).

### Band Guidance (experimental, off by default)

An optional, advisory feature that suggests a mode's customary "watering hole"
and warns when a frequency falls outside the digital band segment — guidance and
defaults, never hard locks. Region-aware (IARU R1/R2/R3), covering 160 m – 70 cm.
Enable with `FLDIGI_BAND_GUIDANCE=on`. It adds the `band_guidance` tool and
enriches `modem`/`frequency` *set* operations with an advisory `guidance` field.
Because band-plan data is hard to get exactly right, it ships experimental and
disabled by default. Design and data: [docs/band-guidance.md](docs/band-guidance.md).

### Remote / distributed setups

fldigi need not run on the same machine. Point the server at it with
`FLDIGI_HOST`/`FLDIGI_PORT`. The fldigi machine must be launched with
`--xmlrpc-server-address 0.0.0.0` to accept LAN connections, and the link should
be kept on a trusted LAN or tunneled over SSH (the XML-RPC interface is
unauthenticated).

**Sandboxed MCP clients (e.g. Claude Desktop):** the client runs the connector
**sandboxed so it can only reach `127.0.0.1`, not LAN addresses** — so a correct
LAN IP for fldigi will time out even though `telnet` to it works. Use the
standalone [mcp-host-bridge](https://github.com/sbrunner-atx/mcp-host-bridge)
relay on the client computer (it knows `fldigi` = port 7362), then set
`FLDIGI_HOST=127.0.0.1`:

```
pipx install mcp-host-bridge             # or download a binary from its releases
mcp-host-bridge install fldigi --to 192.168.1.50
```

Manage it with `mcp-host-bridge status fldigi` / `uninstall fldigi`. The same tool
also bridges N3FJP (for the sibling `n3fjp-mcp`) and any other local service.

## Skills

The [`skills/`](skills/) directory contains agent skills — operating
procedures distilled from live on-air use — bundled with the repo and the
`.mcpb` package:

- **[signal-hunting](skills/signal-hunting/SKILL.md)** — find a station worth
  working the way an operator reads the waterfall: `signal_hunt` names each
  signal's mode from its bandwidth and tone grid (RTTY, CW, PSK, Olivia, MFSK,
  DominoEX, MT63; signatures checked against sigidwiki.com), ranks the one that
  sits still and calls CQ, `tune_to` sets modem and carrier, and twenty seconds
  of text confirms it. Needs `pip install 'fldigi-mcp[hunt]'` (numpy,
  sounddevice) and the **Audio input device** setting; where the server does not
  run beside the receiver (sandbox, remote fldigi), `fldigi-mcp-tap` runs there
  and the server asks it over HTTP (**Signal-hunt tap URL**); without any audio it
  falls back to stepping fldigi's `search_up`. Verified on five recordings of known
  mode, 5 of 5. Receive only.
- **[fldigi-operating](skills/fldigi-operating/SKILL.md)** — TX/RX handoff
  done right (`^r` return-to-receive via `transmit → send`, `abort` as the
  panic button, never poll the TX buffer), RX-buffer polling discipline
  (delta reads, the no-echo rule, restart detection), and a reference CQ
  loop. Field-proven during ARRL Field Day 2026.

The **[Operating Skills Field Guide](docs/operating-skills-field-guide.pdf)**
(PDF) documents these skills and their companion `contest-operating` from the
sibling [n3fjp-mcp](https://github.com/sbrunner-atx/n3fjp-mcp) — skills
at a glance, installation, a plain-language "Your first session — Claude for
hams" chapter for operators new to AI, the operating standard, the
special-case playbook, and worked examples transcribed from ARRL Field Day
2026.

To use with Claude Code / Cowork, copy the skill directory into your
`~/.claude/skills/` (or a project's `.claude/skills/`).

## Development

```bash
uv sync
uv run ruff check .      # lint
uv run pytest            # tests (no running fldigi required)
```

The test suite covers the band-plan logic and the operation maps / type
coercion; it does not require a running fldigi.

## License

[GPL-3.0-or-later](LICENSE) © 2026 Stefan Brunner (AE5VG)

fldigi-mcp is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version. It was MIT-licensed through 0.2.2; the change to GPL-3.0-or-later
(the licence fldigi itself uses) lets this project reuse fldigi code, such as
its multi-channel signal browser, directly. Talking to fldigi over XML-RPC
never required this; porting its decoders does.
