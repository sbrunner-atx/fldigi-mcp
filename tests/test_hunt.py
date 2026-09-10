"""Signal hunt: synthetic signals of known mode must be named and centred, and the
operator-style ranking must prefer the station that sits still and calls CQ.

Real-signal verification (five off-air and synthetic recordings, 5 of 5) lives in
the qso-resolver capture rig; these tests are the part that runs without audio.
"""

from __future__ import annotations

import math

import pytest

np = pytest.importorskip("numpy")
from fldigi_mcp import hunt  # noqa: E402

FS = 12000


def _t(seconds):
    return np.arange(int(seconds * FS)) / FS


def tone(freq, seconds, amp=0.3):
    return amp * np.sin(2 * math.pi * freq * _t(seconds))


def noise(seconds, level=0.01, seed=1):
    return np.random.default_rng(seed).normal(0, level, int(seconds * FS))


def rtty(carrier, shift, seconds, baud=45.45):
    """Random 5-bit characters as FSK, mark above space."""
    rng = np.random.default_rng(2)
    n_bits = int(seconds * baud)
    bits = rng.integers(0, 2, n_bits)
    spb = int(FS / baud)
    n = int(seconds * FS)
    freq = np.repeat(np.where(bits, carrier + shift / 2, carrier - shift / 2), spb)[:n]
    freq = np.pad(freq, (0, n - len(freq)), mode="edge")
    return 0.3 * np.sin(2 * math.pi * np.cumsum(freq) / FS)


def psk31(carrier, seconds):
    """BPSK at 31.25 baud with raised-cosine transitions: a steady 30 Hz line."""
    rng = np.random.default_rng(3)
    baud = 31.25
    spb = int(FS / baud)
    n = int(seconds * FS)
    bits = rng.integers(0, 2, n // spb + 1)
    phase = np.repeat(np.cumsum(bits) % 2, spb)[:n] * math.pi
    env = np.ones(n)
    edge = np.hanning(2 * spb)[:spb]  # smooth every symbol boundary a little
    for k in range(spb, n - spb, spb):
        if phase[k] != phase[k - 1]:
            env[k - spb // 2 : k + spb // 2] = np.concatenate(
                [edge[::-1][: spb // 2], edge[: spb // 2]]
            )
    return 0.3 * env * np.cos(2 * math.pi * carrier * _t(seconds) + phase)


def cw(carrier, seconds, wpm=20):
    """On-off keyed carrier with dits, dahs and element gaps."""
    dit = 1.2 / wpm
    rng = np.random.default_rng(4)
    env, t = [], 0.0
    while t < seconds:
        on = dit * (3 if rng.random() < 0.4 else 1)
        env.append((on, 1.0))
        env.append((dit * (3 if rng.random() < 0.3 else 1), 0.0))
        t += on + dit
    key = np.concatenate([np.full(int(d * FS), v) for d, v in env])[: int(seconds * FS)]
    key = np.pad(key, (0, int(seconds * FS) - len(key)))
    # a real keyer shapes the edges (about 5 ms); hard keying would splatter the line
    key = np.convolve(
        key, np.hanning(int(0.005 * FS)) / np.hanning(int(0.005 * FS)).sum(), mode="same"
    )
    return 0.3 * key * np.sin(2 * math.pi * carrier * _t(seconds))


def olivia(centre, tones, bw, seconds):
    """One of `tones` tones at a time, hopping every symbol (Olivia-like MFSK)."""
    rng = np.random.default_rng(5)
    spacing = bw / tones
    baud = spacing  # Olivia's symbol rate equals the tone spacing
    spb = int(FS / baud)
    n = int(seconds * FS)
    idx = rng.integers(0, tones, n // spb + 1)
    freqs = centre - bw / 2 + spacing / 2 + idx * spacing
    freq = np.repeat(freqs, spb)[:n]
    freq = np.pad(freq, (0, n - len(freq)), mode="edge")
    return 0.3 * np.sin(2 * math.pi * np.cumsum(freq) / FS)


def analyse(x, **kw):
    return hunt.analyse(x, FS, hi=3000, **kw)


def test_rtty_named_with_shift_and_centred():
    x = rtty(1500, 170, 40) + noise(40)
    r = analyse(x, top=1)[0]
    assert r["mode"] == "RTTY" and r["shift"] == 170
    assert abs(r["carrier_hz"] - 1500) < 10
    assert r["fldigi_modem"] == "RTTY"


def test_rtty_450_shift():
    x = rtty(1500, 450, 40, baud=50) + noise(40)
    r = analyse(x, top=1)[0]
    assert r["mode"] == "RTTY" and r["shift"] == 450


def test_psk31_is_a_steady_line():
    x = psk31(1000, 40) + noise(40)
    r = analyse(x, top=1)[0]
    assert r["mode"] == "BPSK31", r
    assert abs(r["carrier_hz"] - 1000) < 10


def test_cw_is_a_keyed_line():
    x = cw(800, 40) + noise(40)
    r = analyse(x, top=1)[0]
    assert r["mode"] == "CW", r
    assert r["off_fraction"] >= 0.07
    assert abs(r["carrier_hz"] - 800) < 10


def test_olivia_grid_gives_tones_and_bandwidth():
    x = olivia(2000, 8, 250, 60) + noise(60)
    r = analyse(x, top=1)[0]
    assert r["mode"] == "Olivia" and r["tones"] == 8 and r["bw"] == 250, r
    assert r["fldigi_modem"] == "OLIVIA-8/250"
    assert abs(r["carrier_hz"] - 2000) < 25


def test_two_signals_ranked_and_separated():
    x = rtty(1200, 170, 40) + 0.5 * psk31(2400, 40) + noise(40)
    rs = analyse(x, top=2)
    modes = {r["mode"] for r in rs}
    assert modes == {"RTTY", "BPSK31"}
    assert rs[0]["db_over_floor"] >= rs[1]["db_over_floor"]


def test_cq_loop_outranks_a_brief_station():
    """Same strength: the station present all along, on a repeating pattern, wins."""
    seconds = 60
    loop = psk31(1000, seconds)
    pattern = np.concatenate([np.ones(int(12 * FS)), np.zeros(int(3 * FS))] * 4)[: len(loop)]
    loop = loop * np.pad(pattern, (0, len(loop) - len(pattern)), constant_values=1)
    brief = psk31(2200, seconds)
    mask = np.zeros_like(brief)
    mask[int(5 * FS) : int(11 * FS)] = 1.0
    x = loop + brief * mask + noise(seconds)
    rs = analyse(x, top=2)
    by = {round(r["carrier_hz"], -2): r for r in rs}
    assert by[1000.0]["persistence"] > by[2200.0]["persistence"]
    assert rs[0]["carrier_hz"] == pytest.approx(1000, abs=20)


def test_confidence_labels():
    r = analyse(rtty(1500, 170, 40) + noise(40), top=1)[0]
    assert r["confidence"] == "high"
    r = analyse(olivia(2000, 8, 250, 60) + noise(60), top=1)[0]
    assert r["confidence"] == "high" and r["grid"] == "frame-peak histogram"
    r = analyse(noise(40, level=0.05), top=1)
    assert all(c["confidence"] in ("none", "low") for c in r)


def test_fldigi_modem_names():
    assert hunt.fldigi_modem("Olivia", {"tones": 16, "bw": 1000}) == "OLIVIA-16/1K"
    assert hunt.fldigi_modem("DominoEX11", {"bw": 262}) == "DOMEX11"
    assert hunt.fldigi_modem("MT63", {"bw": 500}) == "MT63-500"
    assert hunt.fldigi_modem("unknown", {}) is None


def test_signatures_data_is_present():
    assert hunt.RTTY_SHIFTS == [85, 170, 200, 450, 850]
    assert hunt.DOMEX[11] == 262
