"""fldigi-mcp — control the fldigi digital-modem application from MCP clients.

fldigi exposes a built-in XML-RPC control interface. This package wraps that
interface and presents it to MCP clients (Claude Desktop, the MCP Inspector,
etc.) as a set of tools.
"""

from importlib.metadata import PackageNotFoundError, version

try:  # single source of truth: [project].version in pyproject.toml
    __version__ = version("fldigi-mcp")
except PackageNotFoundError:  # running from a source tree with no install
    __version__ = "0.0.0+unknown"
