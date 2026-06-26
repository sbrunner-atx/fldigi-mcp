# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/sbrunner-atx/fldigi-mcp/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/sbrunner-atx/fldigi-mcp/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/sbrunner-atx/fldigi-mcp/releases/tag/v0.1.0
