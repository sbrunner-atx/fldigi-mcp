# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
