"""Band Guidance — advisory watering-hole suggestions and band-plan warnings.

Experimental and opt-in. This module reads the curated band-plan data
(``data/band_plans.yaml``) and turns the current modem + frequency into soft
guidance. It never blocks or changes anything on its own; the server decides
what to do with the advice, and the operator always has the final say.

All frequencies are in Hz.
"""

from __future__ import annotations

from importlib import resources

import yaml

# Within this distance of a calling frequency we consider the operator "already
# there" and stay quiet rather than nagging.
WATERING_HOLE_TOLERANCE_HZ = 2000


def load_data() -> dict:
    """Load and parse the curated band-plan data shipped with the package."""
    ref = resources.files("fldigi_mcp").joinpath("data", "band_plans.yaml")
    with ref.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def mode_category(modem_name: str) -> str:
    """Classify a fldigi modem name into a band-plan category.

    CW lives in the CW allocation; image modes (SSTV/WEFAX) in image conventions;
    everything else digital is treated as DATA (the most conservative choice).
    """
    name = (modem_name or "").upper()
    if name.startswith("CW"):
        return "CW"
    if any(token in name for token in ("SSTV", "WEFAX", "FAX", "HELL")):
        return "IMAGE"
    return "DATA"


def watering_hole_mode(modem_name: str) -> str | None:
    """Map a fldigi modem name to a key in the watering-hole table, or None."""
    name = (modem_name or "").upper()
    table = (
        ("PSK31", ("PSK31", "BPSK31")),
        ("RTTY", ("RTTY",)),
        ("Olivia", ("OLIVIA",)),
        ("MT63", ("MT63",)),
        ("JS8Call", ("JS8",)),
        ("FT8", ("FT8",)),
        ("FT4", ("FT4",)),
        ("JT65", ("JT65",)),
        ("JT9", ("JT9",)),
        ("WSPR", ("WSPR",)),
    )
    for key, needles in table:
        if any(needle in name for needle in needles):
            return key
    return None


def _mhz(hz: float) -> str:
    return f"{hz / 1_000_000:.3f} MHz"


class BandPlan:
    """Region-aware band-plan reasoning built on the curated data file."""

    def __init__(self, region: str = "2", data: dict | None = None) -> None:
        self.region = str(region) if str(region) in {"1", "2", "3"} else "2"
        self._data = data if data is not None else load_data()

    # -- raw lookups ----------------------------------------------------------

    def _bands(self) -> dict:
        return self._data["regions"][self.region]["bands"]

    def band_for(self, hz: float | None) -> str | None:
        """Return the band name whose edges contain ``hz``, or None."""
        if hz is None:
            return None
        for band, spec in self._bands().items():
            lo, hi = spec["edges_hz"]
            if lo <= hz <= hi:
                return band
        return None

    def watering_hole(self, mode: str, band: str | None) -> int | None:
        """Return the calling frequency (Hz) for ``mode`` on ``band``, or None."""
        if not band:
            return None
        return self._data["watering_holes_hz"].get(mode, {}).get(band)

    def segment_check(self, hz: float, category: str) -> dict | None:
        """Return where ``hz`` sits relative to the band's segment for a category."""
        band = self.band_for(hz)
        if band is None:
            return None
        spec = self._bands()[band]
        segment = spec.get("cw_hz" if category == "CW" else "digital_hz")
        if segment is None:
            return {"band": band, "category": category, "segment_hz": None, "in_segment": None}
        lo, hi = segment
        return {
            "band": band,
            "category": category,
            "segment_hz": [lo, hi],
            "in_segment": lo <= hz <= hi,
        }

    # -- advisory guidance ----------------------------------------------------

    def watering_hole_suggestion(self, modem_name: str, hz: float) -> dict | None:
        """Suggest moving to the mode's calling frequency, if not already near it."""
        band = self.band_for(hz)
        mode = watering_hole_mode(modem_name)
        if band is None or mode is None:
            return None
        target = self.watering_hole(mode, band)
        if target is None or abs(hz - target) <= WATERING_HOLE_TOLERANCE_HZ:
            return None
        return {
            "kind": "watering_hole",
            "mode": mode,
            "band": band,
            "region": self.region,
            "current_hz": hz,
            "suggested_hz": target,
            "message": (
                f"The {mode} calling frequency on {band} (Region {self.region}) is "
                f"{_mhz(target)}; you're at {_mhz(hz)}. Want to move there?"
            ),
        }

    def band_plan_warning(self, hz: float, category: str) -> dict | None:
        """Warn if ``hz`` is outside the customary segment for ``category``."""
        check = self.segment_check(hz, category)
        if check is None or check["in_segment"] in (True, None):
            return None
        lo, hi = check["segment_hz"]
        label = "CW" if category == "CW" else "digital/data"
        return {
            "kind": "band_plan",
            "band": check["band"],
            "region": self.region,
            "category": category,
            "segment_hz": [lo, hi],
            "message": (
                f"{_mhz(hz)} is outside the {check['band']} {label} segment "
                f"({_mhz(lo)}–{_mhz(hi)}, Region {self.region}). Advisory only — "
                f"band plans are voluntary."
            ),
        }
