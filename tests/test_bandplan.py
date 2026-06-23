"""Unit tests for Band Guidance logic (no running fldigi required)."""

from __future__ import annotations

import pytest

from fldigi_mcp.bandplan import BandPlan, mode_category, watering_hole_mode
from fldigi_mcp.config import Config

# -- pure helpers -------------------------------------------------------------


def test_mode_category():
    assert mode_category("CW") == "CW"
    assert mode_category("CW (modified)") == "CW"
    assert mode_category("BPSK31") == "DATA"
    assert mode_category("RTTY") == "DATA"
    assert mode_category("MFSK16") == "DATA"
    assert mode_category("SSTV") == "IMAGE"
    assert mode_category("") == "DATA"


def test_watering_hole_mode_mapping():
    assert watering_hole_mode("BPSK31") == "PSK31"
    assert watering_hole_mode("RTTY") == "RTTY"
    assert watering_hole_mode("Olivia 8/250") == "Olivia"
    assert watering_hole_mode("MT63-1000L") == "MT63"
    assert watering_hole_mode("THOR16") is None


# -- band / segment lookups ---------------------------------------------------


def test_band_for_region2():
    bp = BandPlan("2")
    assert bp.band_for(14_074_000) == "20m"
    assert bp.band_for(7_074_000) == "40m"
    assert bp.band_for(50_313_000) == "6m"
    assert bp.band_for(1_000_000) is None  # below all amateur HF bands


def test_watering_hole_lookup():
    bp = BandPlan("2")
    assert bp.watering_hole("PSK31", "20m") == 14_070_000
    assert bp.watering_hole("FT8", "20m") == 14_074_000
    assert bp.watering_hole("FT8", "6m") == 50_313_000


def test_segment_check_in_and_out():
    bp = BandPlan("2")
    # 14.074 is inside the 20 m digital segment (14.070-14.095)
    inside = bp.segment_check(14_074_000, "DATA")
    assert inside["in_segment"] is True
    # 14.230 (SSTV/phone area) is outside the digital segment
    outside = bp.segment_check(14_230_000, "DATA")
    assert outside["in_segment"] is False


# -- advisory guidance --------------------------------------------------------


def test_watering_hole_suggestion_fires_when_off_frequency():
    bp = BandPlan("2")
    g = bp.watering_hole_suggestion("BPSK31", 14_085_000)
    assert g is not None
    assert g["kind"] == "watering_hole"
    assert g["suggested_hz"] == 14_070_000
    assert g["band"] == "20m"


def test_watering_hole_suggestion_quiet_when_already_there():
    bp = BandPlan("2")
    # within tolerance of the PSK31 calling frequency -> no nag
    assert bp.watering_hole_suggestion("BPSK31", 14_070_500) is None


def test_band_plan_warning_only_when_outside():
    bp = BandPlan("2")
    assert bp.band_plan_warning(14_074_000, "DATA") is None
    warn = bp.band_plan_warning(14_230_000, "DATA")
    assert warn is not None and warn["kind"] == "band_plan"


def test_regions_differ():
    # R1 20 m digital starts at 14.070; R2 also 14.070 — but R1 80 m CW extends
    # to 3.570 whereas R2 CW spans the whole 80 m. Spot-check a region-specific
    # boundary: R3 80 m digital starts at 3.535.
    assert BandPlan("3").segment_check(3_540_000, "DATA")["in_segment"] is True
    assert BandPlan("2").segment_check(3_540_000, "DATA")["in_segment"] is False


# -- config -------------------------------------------------------------------


def test_config_defaults(monkeypatch):
    for var in ("FLDIGI_BAND_GUIDANCE", "FLDIGI_REGION", "FLDIGI_CALLSIGN"):
        monkeypatch.delenv(var, raising=False)
    cfg = Config.from_env()
    assert cfg.band_guidance is False
    assert cfg.region == "2"
    assert cfg.transmit_ready is False


def test_config_invalid_region_falls_back(monkeypatch):
    monkeypatch.setenv("FLDIGI_REGION", "9")
    assert Config.from_env().region == "2"


@pytest.mark.parametrize(
    "value,expected",
    [("on", True), ("true", True), ("1", True), ("off", False), ("", False)],
)
def test_band_guidance_flag(monkeypatch, value, expected):
    monkeypatch.setenv("FLDIGI_BAND_GUIDANCE", value)
    assert Config.from_env().band_guidance is expected
