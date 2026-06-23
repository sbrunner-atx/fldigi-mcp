# Contributing to fldigi-mcp

Thanks for your interest in improving fldigi-mcp! This is a ham-radio project —
corrections to band-plan data and fldigi compatibility reports are especially
welcome.

## Development setup

```bash
git clone https://github.com/sbrunner-atx/fldigi-mcp.git
cd fldigi-mcp
uv sync          # creates .venv and installs deps + dev tools
```

## Checks before opening a PR

```bash
uv run ruff check .      # lint
uv run ruff format .     # format
uv run pytest            # tests (no running fldigi required)
```

CI runs the same checks on Python 3.10–3.12. Please keep the test suite green
and add tests for new logic where practical.

## Project layout

```
src/fldigi_mcp/
  client.py     # thin XML-RPC wrapper around fldigi
  config.py     # environment-driven configuration
  methods.py    # operation maps + type coercion for the grouped tools
  server.py     # FastMCP tools (the grouped surface)
  process.py    # launch/stop the fldigi process
  bandplan.py   # Band Guidance logic
  data/band_plans.yaml   # curated band-plan data (cited sources)
tests/          # unit tests
docs/           # design & safety documentation
```

## Guidelines

- **Match fldigi's naming.** Tool and operation names should mirror fldigi's API
  namespaces and on-screen labels so they are recognizable to operators.
- **Never hard-lock the operator.** Band Guidance and similar features are
  advisory only.
- **Respect the transmit gate.** Any new operation that can key the transmitter
  must go through the callsign check (see `_require_transmit_allowed`).
- **Band-plan data needs a cited, dated source.** No guessed frequencies; add a
  `source` to `band_plans.yaml` and keep the validation passing.

## Building the desktop extension (.mcpb)

```bash
npx @anthropic-ai/mcpb pack      # produces fldigi-mcp.mcpb from manifest.json
```

## License

By contributing you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
