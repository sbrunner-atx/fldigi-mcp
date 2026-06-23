# fldigi-mcp

<!-- mcp-name: io.github.sbrunner-atx/fldigi-mcp -->

An [MCP](https://modelcontextprotocol.io/) server for controlling
[fldigi](https://www.w1hkj.org/), the popular amateur-radio digital-modem
application, from MCP-aware clients such as Claude Desktop.

fldigi ships a built-in XML-RPC control interface. `fldigi-mcp` connects to it
and exposes the whole API as a small set of logically-grouped MCP tools, so an
assistant can read the radio's state and drive the modem, rig, log, and
transmitter through plain language.

> **Status:** beta. Full API coverage, callsign-gated transmit, and an optional
> experimental Band Guidance feature. Tested against fldigi 4.2.x.

## Highlights

- **Complete control** — every documented XML-RPC method is reachable, grouped
  into ~14 tools (one permission each) plus a `fldigi_call` escape hatch for the
  long tail and future methods.
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

## Tools

Each tool is one permission and takes an `operation` argument, so e.g. "change
the mode" is a single permission regardless of which underlying method runs.

| Tool | Controls (fldigi area) |
| --- | --- |
| `status` | quick snapshot: version, mode, frequency, T/R, callsign, band |
| `application` | program info + launch/stop the fldigi process (`fldigi.*`) |
| `modem` | Op Mode / modem select, carrier, bandwidth, AFC range, Olivia |
| `frequency` | dial frequency and waterfall sideband |
| `controls` | AFC, SQL, Rev, Lock, RxID, TxID, status fields |
| `transmit` | T/R, Tune, abort, disable/enable Tx, macros, send — **callsign-gated** |
| `rig` | CAT control: mode, frequency, bandwidth, notch, QSY, take/release |
| `log` | Logbook / contest fields; ADIF last/all records |
| `text` | RX/TX text and data streams |
| `spot` | spotting / PSK Reporter |
| `wefax` | WEFAX (weather fax) mode |
| `navtex` | NAVTEX / SitorB mode |
| `band_guidance` | advisory band/watering-hole help (experimental) |
| `fldigi_call` | escape hatch — call any method by name, incl. future ones |

Use `application` → `list_methods` to enumerate every method the running build
supports; anything not surfaced in a group is reachable via `fldigi_call`.

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

## Development

```bash
uv sync
uv run ruff check .      # lint
uv run pytest            # tests (no running fldigi required)
```

The test suite covers the band-plan logic and the operation maps / type
coercion; it does not require a running fldigi.

## License

[MIT](LICENSE) © 2026 Stefan Brunner (AE5VG)
