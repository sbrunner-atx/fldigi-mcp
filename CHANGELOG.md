# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Docs mark the `browser.*` methods as proposed (patch offered upstream 11 Sep 2026, not merged).

## [0.3.0] - 2026-09-11

### Added
- `browser` tool and `signal_hunt method="browser"`: fldigi's Signal Browser over
  XML-RPC, every station the decoder bank holds with its text. Needs the patch in
  `patches/fldigi-4.2.13-browser-xmlrpc.patch` (two methods, `browser.get_channels`
  and `browser.clear`, with an untrimmed per-channel text buffer that keeps line breaks); on stock fldigi
  the tool answers with a hint. Tested on 4.2.13 with four synthetic PSK31 stations
  from 0 to -26 dB, all copied in full.
- FLDIGI-API.md section 16 documents the patched methods; the signal-hunting skill
  and Field Guide say when to use the browser instead of the audio hunt.

### Changed
- Licence changed from MIT to GPL-3.0-or-later (sole author). The MIT choice was
  arbitrary; GPL-3.0-or-later matches fldigi and allows reusing its code (the
  signal-browser decoder bank is the first candidate). Releases up to 0.2.2 remain
  available under MIT.

## [0.2.2] - 2026-09-10

### Fixed
- A blank optional setting in Claude Desktop reaches the server as the literal
  template string (`${user_config.hunt_url}`), which 0.2.1 would have used as the
  tap URL. All settings now treat an unsubstituted template as unset; a blank
  callsign template also keeps the station receive-only, as intended.

## [0.2.1] - 2026-09-10

### Fixed
- The `.mcpb` started the server with `uv run fldigi-mcp`, which does not install
  the optional `hunt` extra, so `signal_hunt` in Claude Desktop reported numpy
  missing. The bundle now runs `uv run --extra hunt fldigi-mcp`. PyPI users were
  unaffected (`pip install 'fldigi-mcp[hunt]'`).

## [0.2.0] - 2026-09-10

### Added
- **Signal hunting.** `signal_hunt` taps the audio fldigi listens to (new setting
  `FLDIGI_AUDIO_DEVICE` / "Audio input device") and returns ranked candidates:
  carrier, mode named from bandwidth and tone structure (RTTY with shift, CW,
  BPSK31/63/125, Olivia with tones and bandwidth, MFSK16, DominoEX, MT63;
  `data/mode_signatures.json`, checked against the Signal Identification Wiki),
  strength, persistence, periodicity, and an operator-style score that ranks the
  station sitting still and calling CQ first. `tune_to` sets modem and carrier
  from a candidate, RxID off during a classified pass. `method="api"` is the
  blind fallback without audio (fldigi `search_up` + `get_quality`).
- Optional extra `fldigi-mcp[hunt]` (numpy, sounddevice); the base server stays
  dependency-free.
- `fldigi-mcp-tap`, a host-side HTTP tap for deployments where the server does not
  run where the audio is (Cowork sandbox, remote fldigi via mcp-host-bridge): set
  `FLDIGI_HUNT_URL` and `signal_hunt` asks it instead of the sound card. All-zero
  audio is reported as a warning naming the microphone-permission fix.
- Skill `signal-hunting` and a chapter in the Operating Skills Field Guide.
- Tests with synthetic RTTY, PSK31, keyed CW, Olivia and mixed signals. The
  analyser was verified on five real recordings of known mode, 5 of 5.

### Notes
- Contestia shares Olivia's grid and THOR shares DominoEX's; only RSID
  separates them. Symbol rate is the next feature. Everything here is receive only.

## [0.1.6] - 2026-09-09

### Added
- **Full catalog coverage.** Every one of fldigi's 174 XML-RPC methods is now
  reachable through a named operation. New tools `flmsg` (online, available,
  transfer, squelch, get_data), `io` (in_use, enable_kiss, enable_arq) and
  `legacy` (the 14 deprecated methods and the `main.flmsg_*` aliases, each with
  its current equivalent named). New operations: `modem` get_io_names; `transmit`
  tx_timing, char_rates, char_timing; `rig` set_smeter, set_pwrmeter; `text`
  get_rx (value=[start, length]) and add_tx_bytes; `log` set contest_counter.
- `tests/test_coverage.py` and the shipped catalog
  `src/fldigi_mcp/data/fldigi_methods.json` (the `fldigi.list` output of 4.2.13):
  the suite fails if a catalog method has no operation, if an operation targets a
  method fldigi does not serve, or if an argument kind disagrees with fldigi's
  signature. `scripts/refresh_method_catalog.py` regenerates the catalog.
- New argument kinds: `6` (base64 bytes) and two-argument `ii` / `si`.

### Fixed
- **Array parameters.** `rig.set_modes` and `rig.set_bandwidths` were spread into
  positional strings, which fldigi answers with `type error`; they are now sent as
  one XML-RPC array. `wefax.send_file` now takes `[filename, timeout]` per its
  `s:si` signature.
- **`rig` `take_control` / `release_control` removed**: no fldigi 4.2.x build serves
  those methods; the calls could never succeed.
- `main.get_tx_timing` / `main.get_char_timing` are called with the base64
  parameter the live build actually accepts (its `fldigi.list` signature is wrong).
- `application` `launch` picks the newest installed fldigi by version number
  (4.2.13 over 4.2.9), not by string order.

### Changed
- Supported fldigi release is **4.2.13**, verified live 2026-09-09; the XML-RPC
  surface is identical to 4.2.11. Docs updated (README, FLDIGI-API.md gotchas
  11 to 15, FLDIGI-API-SPEC.md rows for the timing and array methods).

## [0.1.5] - 2026-09-09

### Fixed
- **Pin the MCP SDK below 2.0** (`mcp[cli]>=1.2.0,<2`). mcp 2.x renamed
  `FastMCP` to `MCPServer` and moved `mcp.server.fastmcp`, so a fresh install
  from PyPI (`uvx fldigi-mcp`) resolved 2.x and failed at import. The `.mcpb`
  was unaffected because it ships `uv.lock`. No functional changes.

## [0.1.4] - 2026-07-31

### Changed
- Docs: updated references to the sibling logging project, which was **renamed
  `contest-mcp` → `n3fjp-mcp`** (README, the Operating Skills Field Guide, and the
  `fldigi-operating` skill). No code changes.
- **Regenerated the compiled Operating Skills Field Guide PDF**
  (`docs/operating-skills-field-guide.pdf`, shipped inside the `.mcpb`) from the
  corrected HTML so it no longer carries stale `contest-mcp` references — a text
  rename can't touch the binary. 0 `contest-mcp` refs remain.

### Added
- CI: a `release.yml` workflow that publishes to PyPI via **Trusted Publishing
  (OIDC)** on GitHub Release — no API tokens.

## [0.1.3] - 2026-07-29

### Fixed
- Field guide: coherent pseudonymization of garbled callsign fragments in
  the worked-example transcripts (fragments are now fragments of the
  sample calls, not of any real callsign).

## [0.1.2] - 2026-07-29

### Added
- **`fldigi-operating` agent skill** (`skills/fldigi-operating/SKILL.md`),
  bundled in the repo and the `.mcpb` package. Distills the TX/RX handoff
  discipline field-proven at ARRL Field Day 2026: end every over with `^r`
  via `transmit → send` (never poll the TX buffer), `abort` as the
  immediate stop, RX-buffer delta polling with the no-echo rule and
  fldigi-restart detection, and a reference CQ loop. README now has a
  **Skills** section describing usage.
- **Operating Skills Field Guide** (`docs/operating-skills-field-guide.pdf`)
  covering this skill and n3fjp-mcp's `contest-operating`: skills at a
  glance, TOC, installation, a plain-language "Your first session — Claude
  for hams" chapter for operators new to AI, the six-rule operating
  standard, the special-case playbook, and worked examples transcribed from
  ARRL Field Day 2026. Regenerable HTML/CSS sources under `docs/brand/`
  (AE5VG personal amateur-radio brand — dark ink, signal amber, Morse
  wordmark).

## [0.1.1] - 2026-06-26

### Added
- New read-only **`diagnostics`** tool: reports the resolved `FLDIGI_HOST`/
  `FLDIGI_PORT`, transmit-gate state, this process's Python/hostname, and the
  host's network interfaces — **without connecting to fldigi** — so you can tell
  whether the connector can even see the target's network (host-side vs.
  sandboxed).

### Changed
- **Structured connection errors.** When fldigi can't be reached, the message now
  carries `target=host:port`, the symbolic `errno`
  (`ETIMEDOUT`/`EHOSTUNREACH`/`ENETUNREACH`/`ECONNREFUSED`/`ENOTFOUND`), the
  process hostname, and the IPv4 addresses seen — and, for a **non-loopback**
  host, a pointer to the [mcp-host-bridge](https://github.com/sbrunner-atx/mcp-host-bridge)
  fix. Post-connect XML-RPC faults keep their own message.
- Docs: when fldigi runs on another computer and a **sandboxed** MCP client (e.g.
  Claude Desktop) can only reach loopback, point users to the standalone
  [mcp-host-bridge](https://github.com/sbrunner-atx/mcp-host-bridge) relay
  (`mcp-host-bridge install fldigi --to <ip>`, then `FLDIGI_HOST=127.0.0.1`).

## [0.1.0] - 2026-06-22

Initial release.

### Added
- MCP server exposing fldigi's XML-RPC control interface, talking directly to
  fldigi via Python's standard-library `xmlrpc.client`.
- **Full API coverage** organised into ~14 logically-grouped tools (one
  permission each): `status`, `application`, `modem`, `frequency`, `controls`,
  `transmit`, `rig`, `log`, `text`, `spot`, `wefax`, `navtex`, `band_guidance`,
  and a `fldigi_call` escape hatch for any remaining or future methods.
- Tool and operation names aligned with fldigi's own API namespaces and
  on-screen control labels (Op Mode, AFC, SQL, Rev, Lock, RxID/TxID, T/R, Tune).
- **Transmit safety**: the operator callsign is the single transmit gate. With
  no callsign configured the station is receive-only and no tool can key the
  radio. Enforced server-side, independent of client permissions.
- Per-operation XML-RPC type coercion (double/int/bool/string/array) so setters
  like `set_frequency` and `set_squelch_level` are sent the type fldigi expects.
- Cross-platform process management (`application` launch/stop) for macOS,
  Windows, and Linux/Raspberry Pi.
- **Band Guidance** (experimental, off by default): region-aware advisory
  watering-hole suggestions and out-of-segment warnings, backed by curated and
  validated IARU R1/R2/R3 band-plan data for 160 m – 70 cm. Never hard-locks.
- Configuration via environment variables (`FLDIGI_HOST`, `FLDIGI_PORT`,
  `FLDIGI_CALLSIGN`, `FLDIGI_BAND_GUIDANCE`, `FLDIGI_REGION`, `FLDIGI_PATH`),
  surfaced as a settings form in the packaged desktop extension.
- Unit test suite (band-plan logic, operation maps, type coercion) and a
  GitHub Actions CI workflow running ruff and pytest on Python 3.10–3.12.
- Documentation: README, installation & safety model, and Band Guidance design.

[Unreleased]: https://github.com/sbrunner-atx/fldigi-mcp/compare/v0.1.5...HEAD
[0.1.5]: https://github.com/sbrunner-atx/fldigi-mcp/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/sbrunner-atx/fldigi-mcp/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/sbrunner-atx/fldigi-mcp/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/sbrunner-atx/fldigi-mcp/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/sbrunner-atx/fldigi-mcp/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/sbrunner-atx/fldigi-mcp/releases/tag/v0.1.0
