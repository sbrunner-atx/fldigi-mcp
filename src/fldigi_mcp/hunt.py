"""Signal hunt: look at the audio the way an operator looks at the waterfall.

Given a few seconds of receiver audio, find the signals, name their mode from
bandwidth and tone structure (``data/mode_signatures.json``, checked against the
Signal Identification Wiki), and rank them the way a contest operator does: the
station that sits still and calls CQ scores highest.

Three measurements per signal, all from one buffer:

* strength      - max-hold spectrum over 5-second blocks, dB over the noise floor,
                  so a station that transmits for part of the window shows at full
                  strength instead of being averaged away
* persistence   - fraction of the blocks in which the signal is present at the same
                  carrier; a CQ loop scores near 1, an answering station vanishes
* periodicity   - autocorrelation of the on/off envelope at lags of 8 to 60 s; a CQ
                  loop repeats, a QSO in progress does not

Mode naming: two narrow lines a standard shift apart is RTTY (carrier at the
midpoint); one 30 Hz line is PSK31 unless it is keyed on and off, which makes it
CW; an evenly spaced grid is Olivia / Contestia / MFSK / DominoEX / THOR, with the
tone count from bandwidth over spacing; a continuous flat block is MT63. Contestia
shares Olivia's grid and THOR shares DominoEX's; only RSID separates those.

Audio comes from a live tap on the receiver's input device (optional extra
``fldigi-mcp[hunt]``: numpy + sounddevice) or from a WAV file. fldigi's XML-RPC
exposes no spectrum, which is why a tap is needed; ``api_hunt`` below is the
blind fallback that steps ``modem.search_up`` and reads ``modem.get_quality``.

The analysis is deliberately numpy-only and stateless: one buffer in, a ranked
list of candidates out. Verified on 10 Sep 2026 against five recordings of known
mode (PSK31, CW, RTTY 170, RTTY 450, Olivia 8/250): 5 of 5.
"""

from __future__ import annotations

import json
import wave
from importlib import resources

try:  # optional extra; the server imports this module unconditionally
    import numpy as np
except ImportError:  # pragma: no cover - exercised only without the extra
    np = None

SIGNATURES = json.loads(
    resources.files("fldigi_mcp").joinpath("data/mode_signatures.json").read_text()
)
MODES = SIGNATURES["modes"]
RTTY_SHIFTS = MODES["RTTY"]["shifts_hz"]
DOMEX = {int(k): v["bw"] for k, v in MODES["DominoEX"]["submodes"].items()}


class HuntUnavailable(RuntimeError):
    """numpy (and sounddevice, for a live tap) are not installed."""


def _need_numpy() -> None:
    if np is None:
        raise HuntUnavailable(
            "signal hunting needs numpy (and sounddevice for a live tap): "
            "pip install 'fldigi-mcp[hunt]'"
        )


# --------------------------------------------------------------------------- audio in


def read_wav(path: str) -> tuple:
    """Return (samples as float64 mono, sample rate)."""
    _need_numpy()
    with wave.open(path) as w:
        fs = w.getframerate()
        n = w.getnchannels()
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64)
    if n > 1:
        raw = raw.reshape(-1, n).mean(axis=1)
    return raw / 32768.0, fs


def list_devices() -> list[dict]:
    """Input devices sounddevice can open (name and index), for FLDIGI_AUDIO_DEVICE."""
    _need_numpy()
    import sounddevice as sd

    out = []
    for i, d in enumerate(sd.query_devices()):
        if d.get("max_input_channels", 0) > 0:
            out.append(
                {"index": i, "name": d["name"], "default_samplerate": d.get("default_samplerate")}
            )
    return out


def capture(seconds: float, device: str | int | None = None, fs: int = 12000) -> tuple:
    """Tap `seconds` of audio from an input device (name substring or index)."""
    _need_numpy()
    import sounddevice as sd

    dev = device
    if isinstance(device, str) and not device.isdigit():
        matches = [d for d in list_devices() if device.lower() in d["name"].lower()]
        if not matches:
            raise HuntUnavailable(f"no input device matching {device!r}; see list_devices()")
        dev = matches[0]["index"]
    elif isinstance(device, str):
        dev = int(device)
    x = sd.rec(int(seconds * fs), samplerate=fs, channels=1, dtype="float32", device=dev)
    sd.wait()
    return x[:, 0].astype(np.float64), fs


# --------------------------------------------------------------------------- analysis


def analyse(
    x, fs: int, lo: float = 300.0, hi: float = 3400.0, top: int = 4, block_s: float = 5.0
) -> list[dict]:
    """Rank the signals in `x`: mode, parameters, carrier, strength, persistence, periodicity."""
    _need_numpy()
    n = 8192 if fs >= 11000 else 4096  # ~1.5 Hz bins: resolves Olivia's 31 Hz grid
    win = np.hanning(n)
    f = np.fft.rfftfreq(n, 1 / fs)
    df = f[1] - f[0]
    blk = max(n, int(block_s * fs))
    blocks = []
    for b0 in range(0, max(1, len(x) - n), blk):
        seg = x[b0 : b0 + blk]
        acc = np.zeros(n // 2 + 1)
        k = 0
        for i in range(0, len(seg) - n, n // 2):
            acc += np.abs(np.fft.rfft(seg[i : i + n] * win)) ** 2
            k += 1
        if k:
            blocks.append(10 * np.log10(acc / k + 1e-12))
    if not blocks:
        return []
    B = np.array(blocks)
    mh = B.max(axis=0)
    band = (f >= lo) & (f <= hi)
    floor = float(np.median(np.median(B, axis=0)[band]))
    s = mh - floor
    sm = np.convolve(s, np.ones(21) / 21, mode="same")

    def block_at(i):
        thr = sm[i] - 6
        a = i
        while a > 0 and sm[a - 1] > thr:
            a -= 1
        b = i
        while b < len(sm) - 1 and sm[b + 1] > thr:
            b += 1
        return a, b

    def tones_in(a, b):
        # average over EVERY block in which the signal is present: a hopping mode
        # shows its whole tone grid only over tens of seconds of on-time
        pw = B[:, a : b + 1].mean(axis=1)
        on = pw >= floor + 6
        if on.sum() == 0:
            on = pw >= pw.max() - 8
        seg = B[on][:, a : b + 1].mean(axis=0) - floor
        base = np.percentile(seg, 20)
        idx = [
            j
            for j in range(1, len(seg) - 1)
            if seg[j] > seg[j - 1] and seg[j] >= seg[j + 1] and seg[j] - base >= 3
        ]
        tones = []
        for j in idx:
            if not tones or (j - tones[-1]) * df >= 8:
                tones.append(j)
        return [float(f[a + j]) for j in tones], on

    def grid_of(a, b):
        """The dot grid an operator sees: per 30 ms frame, the peak frequency inside the
        block; a histogram of those peaks shows the discrete tone positions of a hopping
        mode (one tone on at a time), which the AVERAGED spectrum cannot, because each
        Olivia tone is as wide as the tone spacing and the lines merge into a flat block.
        Returns (positions in Hz, median spacing) for positions holding >= 3% of frames."""
        win_n = int(0.032 * fs)  # one Olivia/MFSK symbol; a longer window
        nfft = 4096  # straddles symbols and lands between tones
        hop = int(0.016 * fs)
        fr = np.fft.rfftfreq(nfft, 1 / fs)
        lo_hz, hi_hz = f[a] - 5, f[b] + 5
        sel = np.where((fr >= lo_hz) & (fr <= hi_hz))[0]
        if len(sel) < 4:
            return [], None
        w2 = np.hanning(win_n)
        peaks, powers = [], []
        for i in range(0, len(x) - win_n, hop):
            sp = np.abs(np.fft.rfft(x[i : i + win_n] * w2, n=nfft)[sel]) ** 2
            peaks.append(fr[sel[int(np.argmax(sp))]])
            powers.append(sp.max())
        peaks, powers = np.array(peaks), np.array(powers)
        strong = powers >= np.percentile(powers, 50)  # frames where the signal is on
        if strong.sum() < 20:
            return [], None
        hist, edges = np.histogram(peaks[strong], bins=np.arange(lo_hz, hi_hz + 4, 4.0))
        pos = [
            float((edges[k] + edges[k + 1]) / 2) for k in np.where(hist >= 0.03 * strong.sum())[0]
        ]
        merged = []
        for p_ in pos:  # merge the bins of one tone (a 31 baud tone is ~30 Hz wide)
            if merged and p_ - merged[-1][-1] <= 10.0:
                merged[-1].append(p_)
            else:
                merged.append([p_])
        pos = [float(np.mean(m)) for m in merged]
        sp_ = float(np.median(np.diff(pos))) if len(pos) >= 3 else None
        return pos, sp_

    def off_fraction(centre_hz, half_bw=60.0):
        """Fraction of active time inside keying gaps of 40 ms or longer, in +-half_bw
        around centre. Gap DURATION is the discriminator: a CW element gap is 40 ms or
        more even at 30 wpm, a PSK phase-reversal dip lasts a few milliseconds, and a
        fade lasts seconds, which the local one-second reference removes. Frame power
        is taken incoherently (8 ms window, 5 ms hop) so phase cannot fake a gap."""
        win_n = int(0.008 * fs)
        hop = int(0.005 * fs)
        nfft = 1024
        fr = np.fft.rfftfreq(nfft, 1 / fs)
        sel = (fr >= centre_hz - half_bw) & (fr <= centre_hz + half_bw)
        w2 = np.hanning(win_n)
        env = np.sqrt(
            np.array(
                [
                    float((np.abs(np.fft.rfft(x[i : i + win_n] * w2, n=nfft)[sel]) ** 2).sum())
                    for i in range(0, len(x) - win_n, hop)
                ]
            )
        )
        if len(env) < 200:
            return 0.0
        on_level = np.percentile(env, 90)
        if on_level <= 0:
            return 1.0
        from numpy.lib.stride_tricks import sliding_window_view as swv

        pad = np.pad(env, 200, mode="edge")  # +-1 s at 5 ms hops
        local = swv(pad, 401).max(axis=1)
        # active = the neighbourhood is loud, not the frame itself: a keying gap on a
        # strong signal is silent for 60 ms and must count; a pause between overs is
        # silent for seconds and must not
        active = local > 0.05 * on_level
        if active.sum() < 200:
            return 0.0
        low = (env / np.maximum(local, 1e-9) < 0.25) & active
        runs = np.diff(np.concatenate([[0], low.astype(int), [0]]))
        starts, ends = np.where(runs == 1)[0], np.where(runs == -1)[0]
        gap = sum(e - b for b, e in zip(starts, ends, strict=True) if e - b >= 8)  # >= 40 ms
        return float(gap / active.sum())

    def periodicity(on_blocks):
        """Peak autocorrelation of the on/off pattern at lags of 2 blocks or more (8 s+
        at 5 s blocks): a CQ loop repeats, a QSO does not. Needs a window long enough."""
        v = on_blocks.astype(float) - on_blocks.mean()
        if len(v) < 6 or v.std() == 0:
            return None
        best = 0.0
        for lag in range(2, len(v) // 2 + 1):
            c = float((v[:-lag] * v[lag:]).mean() / (v.var() + 1e-12))
            best = max(best, c)
        return round(best, 2)

    results, used = [], np.zeros_like(sm, dtype=bool)
    for i in np.argsort(sm)[::-1]:
        if not band[i] or used[i] or sm[i] < 6:
            continue
        a, b = block_at(i)
        used[max(0, a - 60) : b + 60] = True
        width = (b - a) * df
        centre = float(f[(a + b) // 2])
        if width > 2200:
            continue
        tones, on = tones_in(a, b)
        width = (b - a) * df
        gpos, gsp = (
            grid_of(a, b) if width > 60 else ([], None)
        )  # single lines are judged by width, not by a grid
        if len(gpos) >= 4 and gsp:  # the dot grid beats the averaged lines
            tones, spacing_grid = gpos, gsp
        else:
            spacing_grid = None
        pw = B[:, a : b + 1].mean(axis=1)
        present = pw >= floor + 6
        avg_on = B[on].mean(axis=0)
        tb = [int(round((t - f[0]) / df)) for t in tones] or [i]
        duty_db = float(np.mean([mh[k] - avg_on[k] for k in tb]))
        spacing = spacing_grid or (float(np.median(np.diff(tones))) if len(tones) >= 3 else None)
        mode, carrier, extra = "unknown", centre, {}
        peak_f = float(f[i])
        partner, best = None, 0.0
        if width < 60:
            for shift in RTTY_SHIFTS:
                for sign in (-1, 1):
                    j = int(round((peak_f + sign * shift - f[0]) / df))
                    if 3 < j < len(s) - 4:
                        k = j - 3 + int(np.argmax(s[j - 3 : j + 4]))
                        if s[k] >= 0.5 * s[i] and s[k] >= 6 and s[k] > best:
                            best, partner = s[k], (shift, float(f[k]))
        if partner:
            shift, pf = partner
            mode, carrier, extra = "RTTY", (peak_f + pf) / 2, {"shift": shift}
            k = int(round((pf - f[0]) / df))
            used[max(0, k - 60) : k + 60] = True  # the partner line is the same signal
        elif width <= 45:  # one line: keying gaps decide CW vs PSK
            off = off_fraction(peak_f)
            mode, carrier = ("CW", peak_f) if off >= 0.05 else ("BPSK31", carrier)
            extra = {"off_fraction": round(off, 2)}
        elif 50 <= width <= 80 and len(tones) <= 3:
            mode = "BPSK63"
        elif 100 <= width <= 150 and len(tones) <= 3:
            mode = "BPSK125"
        elif spacing and len(tones) >= 4:
            if (
                25 <= spacing <= 40
                or 55 <= spacing <= 70
                or 13 <= spacing <= 18
                or 120 <= spacing <= 130
            ):
                bw = min((125, 250, 500, 1000, 2000), key=lambda v: abs(v - width))
                nt = min((4, 8, 16, 32, 64), key=lambda t: abs(t - bw / spacing))
                if 13 <= spacing <= 18 and 260 <= width <= 360 and nt in (16, 32):
                    mode = "MFSK16"
                else:
                    mode, extra = "Olivia", {"tones": nt, "bw": bw}
            else:
                for n_, bw in DOMEX.items():
                    if abs(width - bw) <= 0.12 * bw and abs(spacing - bw / 18) <= 2.5:
                        mode, extra = f"DominoEX{n_}", {"bw": bw}
        if mode == "unknown" and duty_db <= 3.5 and len(tones) >= 8:
            bw = min((500, 1000, 2000), key=lambda v: abs(v - width))
            if abs(width - bw) <= 0.15 * bw:
                mode, extra = "MT63", {"bw": bw}
        if any(abs(r["carrier_hz"] - carrier) < 100 for r in results):
            continue  # same signal seen from its other line
        # confidence: high when the mode was read from a real grid (frame-peak histogram)
        # or from strong lines; a hopping mode inferred from the averaged spectrum alone,
        # or anything under 10 dB, is a guess and should not buy a decode pass by itself
        if mode == "unknown":
            confidence = "none"
        elif mode in ("RTTY", "CW", "BPSK31", "BPSK63", "BPSK125") and float(sm[i]) >= 10:
            confidence = "high"
        elif spacing_grid and float(sm[i]) >= 10:
            confidence = "high"
        else:
            confidence = "low"
        strength = float(sm[i])
        persistence = float(present.mean())
        per = periodicity(present)
        score = strength * (0.5 + persistence) * (1.0 + (per or 0.0))
        results.append(
            {
                "carrier_hz": round(carrier, 1),
                "mode": mode,
                **extra,
                "db_over_floor": round(strength, 1),
                "width_hz": round(width, 1),
                "tones": len(tones),
                "tone_spacing_hz": round(spacing, 1) if spacing else None,
                "grid": "frame-peak histogram" if spacing_grid else "averaged spectrum",
                "duty_db": round(duty_db, 1),
                "persistence": round(persistence, 2),
                "periodicity": per,
                "score": round(score, 1),
                "confidence": confidence,
                "fldigi_modem": fldigi_modem(mode, extra),
            }
        )
        if len(results) >= top:
            break
    results.sort(key=lambda r: -r["score"])
    return results


def fldigi_modem(mode: str, extra: dict) -> str | None:
    """The modem name fldigi wants for a classified signal (modem.set_by_name)."""
    if mode == "Olivia":
        bw = {1000: "1K", 2000: "2K"}.get(extra.get("bw"), str(extra.get("bw")))
        return f"OLIVIA-{extra.get('tones')}/{bw}"
    if mode.startswith("DominoEX"):
        return "DOMEX" + mode[len("DominoEX") :]
    if mode == "MT63":
        return f"MT63-{extra.get('bw')}"
    if mode in ("RTTY", "CW", "BPSK31", "BPSK63", "BPSK125", "MFSK16"):
        return mode
    return None


def api_hunt(client, modems: list[str], settle_s: float = 3.0, max_steps: int = 12) -> list[dict]:
    """Blind fallback without audio: for each modem, step modem.search_up across the
    passband and read modem.get_quality. Slow (seconds per step) and it only finds
    what the current modem can lock to, but it needs nothing beyond the XML-RPC."""
    import time

    found = []
    for m in modems:
        client.call("modem.set_by_name", m)
        client.call("modem.set_carrier", 400)
        seen = set()
        for _ in range(max_steps):
            client.call("modem.search_up")
            time.sleep(settle_s)
            c = int(client.call("modem.get_carrier"))
            if c in seen:
                break
            seen.add(c)
            q = float(client.call("modem.get_quality"))
            if q >= 30:
                found.append(
                    {
                        "carrier_hz": c,
                        "mode": m,
                        "quality": round(q, 1),
                        "fldigi_modem": m,
                        "method": "api",
                    }
                )
    found.sort(key=lambda r: -r["quality"])
    return found
