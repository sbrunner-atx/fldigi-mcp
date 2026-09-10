"""Runtime configuration for the fldigi MCP server.

Settings are read from environment variables. In development you set these in
the Claude Desktop server entry's ``env`` block; in the packaged ``.mcpb``
desktop extension they are surfaced as a settings form and passed through as the
same environment variables. The code therefore does not care which one set them.

Transmit policy: the **callsign is the single transmit gate**. If a callsign is
configured, transmit tools are available (subject to the client's own approval
prompt). If it is blank, transmit is impossible — the server refuses to key the
radio. There is intentionally no separate "enable transmit" flag.

Band Guidance is an optional, **experimental** advisory feature, **off by
default**. When on, it suggests a mode's customary calling frequency and warns
when a frequency falls outside the digital band segment for the chosen region.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_TRUE = {"1", "true", "yes", "on"}
_REGIONS = {"1", "2", "3"}


def _as_bool(value: str | None) -> bool:
    return value is not None and str(value).strip().lower() in _TRUE


def _setting(name: str, default: str = "") -> str:
    """An environment setting, with Claude Desktop's unsubstituted templates treated as
    unset: a blank optional user_config field arrives as the literal '${user_config.x}'."""
    v = os.environ.get(name, default).strip()
    return default if v.startswith("${") else v


@dataclass
class Config:
    """Resolved server configuration."""

    host: str
    port: int
    callsign: str
    band_guidance: bool
    region: str
    audio_device: str
    hunt_url: str

    @property
    def transmit_ready(self) -> bool:
        """True when transmit is permitted, i.e. a (non-blank) callsign is set."""
        return bool(self.callsign)

    @classmethod
    def from_env(cls) -> Config:
        region = _setting("FLDIGI_REGION", "2")
        if region not in _REGIONS:
            region = "2"
        return cls(
            host=_setting("FLDIGI_HOST", "127.0.0.1"),
            port=int(_setting("FLDIGI_PORT", "7362") or "7362"),
            callsign=_setting("FLDIGI_CALLSIGN").upper(),
            band_guidance=_as_bool(_setting("FLDIGI_BAND_GUIDANCE")),
            region=region,
            # input device the signal hunt taps (name substring or index); blank = system default
            audio_device=_setting("FLDIGI_AUDIO_DEVICE"),
            # a host-side fldigi-mcp-tap to ask instead of the local sound card
            # (sandbox, or fldigi on another machine)
            hunt_url=_setting("FLDIGI_HUNT_URL").rstrip("/"),
        )
