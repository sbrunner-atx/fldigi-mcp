---
name: signal-hunting
description: >
  Find a station worth working the way an operator reads the waterfall: look at
  the receiver audio, name each signal's mode from its bandwidth and tone grid,
  rank the ones that sit still and call CQ, tune fldigi to the best one, and
  confirm by reading twenty seconds of text before handing over to
  fldigi-operating for the QSO. Use whenever the operator says "find me
  someone to work", "what is that signal", "is anyone calling CQ", or when a
  contest needs the next station. Receive only; nothing here keys the radio.
---

# Signal hunting: find, name, tune, confirm

## What the tools see

`signal_hunt` taps a few seconds of the audio fldigi is listening to (the
`FLDIGI_AUDIO_DEVICE` setting names the input device; the default is the
system input) and returns ranked candidates. It needs the optional extra
`fldigi-mcp[hunt]` (numpy and sounddevice). Each candidate has:

| field | meaning |
| --- | --- |
| `carrier_hz` | where the waterfall cursor goes (fldigi's audio carrier; `Freq` = dial + carrier) |
| `mode`, `shift`, `tones`, `bw` | RTTY with its shift; CW; BPSK31/63/125; Olivia with tones and bandwidth; MFSK16; DominoEX; MT63; or `unknown` |
| `fldigi_modem` | the exact name `tune_to` needs, e.g. `OLIVIA-8/250` |
| `db_over_floor` | strength |
| `persistence` | fraction of the window the signal was present at that carrier |
| `periodicity` | how strongly the on/off pattern repeats; a CQ loop scores high |
| `score` | strength weighted by persistence and periodicity: the CQing station wins |

fldigi's XML-RPC exposes no spectrum, which is why the tap exists. Without
audio access, `signal_hunt` with `method="api"` steps `modem.search_up` for each
modem and reads `modem.get_quality`. It is slow and only finds what the current
modem can lock to; use it when the tap is unavailable, not by preference.

## With the Signal Browser patch (proposed upstream, not merged)

fldigi's own Signal Browser is a bank of up to 30 demodulators with DCD; it copies
PSK, RTTY and CW stations too faint for a spectrum to rank. On a fldigi built with
`patches/fldigi-4.2.13-browser-xmlrpc.patch` (see `browser available`), use it as
the finder for those modes: set the modem family with `tune_to` (any carrier), wait
20 s, then `browser channels` or `signal_hunt method="browser"`. Each channel gives
the carrier and the text already copied, so the "confirm" step is done before you
tune. The browser names no mode; use the audio hunt first when the band's mode is
not known. Without the patch both calls answer with a hint and nothing else changes.

## The loop

1. **Hunt.** `signal_hunt(seconds=20)`. For a contest, pass the contest mode so
   only that mode is ranked, e.g. `mode="RTTY"`, and use `seconds=40` so a CQ
   loop can show its period. A fast look for "what is that" is `seconds=10`.
2. **Read the candidates like a waterfall.** Highest score first. A candidate
   with persistence near 1 and periodicity above 0.4 is a station calling CQ
   on its own; persistence 0.3 with no periodicity is one side of a QSO in
   progress, worth listening to but not calling.
3. **Tune.** `tune_to(carrier_hz, fldigi_modem)`. RxID stays off during a
   classified pass; another station's RSID burst would otherwise retune the
   modem mid-pass. Leave it on only when the mode came back `unknown`.
4. **Confirm in twenty seconds.** `text` read after 20 s. You are looking for
   `CQ` and a callsign-shaped token, twice. If the text is garbage, `modem`
   `get_quality` below 30 means the carrier is off; try the second candidate or
   re-hunt. If the text is fine but it is a QSO in progress, wait for `SK` or
   `73` before calling.
5. **Hand over.** Once a CQ and a callsign are confirmed, switch to the
   `fldigi-operating` skill for the exchange; `contest-operating` (n3fjp-mcp)
   for a contest exchange and its logging.

## What the names mean, and where they come from

The signatures are in `data/mode_signatures.json`, checked against the Signal
Identification Wiki (sigidwiki.com, Category:Amateur_Radio) and the fldigi
manual. RTTY is two narrow lines a standard shift apart (170 Hz in amateur use,
450 and 850 commercial) that key against each other, with the carrier at the
midpoint; two PSK31 stations that merely sit 170 Hz apart change independently
and are named as two stations, not one RTTY signal. PSK31 is a single 30 Hz
line; CW is the same line keyed on and off, told apart by the element gaps. The
hopping modes show as a grid of discrete tone positions when you look at where
the energy is from one 30 ms frame to the next, which is what the waterfall's
dots are: Olivia (tones = bandwidth / spacing, 8/250 the common one), MFSK16
(16 tones at 15.6 Hz), DominoEX and THOR (18 tones). MT63 is a flat continuous
block 500, 1000 or 2000 Hz wide.

Two pairs cannot be separated by the spectrum alone: Contestia looks like
Olivia and THOR like DominoEX. If a candidate decodes as nothing in Olivia,
try `CONTESTIA` with the same tones and bandwidth; if a station sends RSID,
fldigi's RxID settles it.

## Limits, stated

- Verified on five recordings of known mode (PSK31, CW, RTTY 170 and 450 Hz,
  Olivia 8/250): 5 of 5. That is a small set; treat `unknown` as honest.
- One tap window is one look. A station that transmits for ten seconds of your
  twenty scores lower than it deserves; hunt again before giving up on a band.
- Symbol rate is not measured yet; it is what would separate Contestia from
  Olivia and THOR from DominoEX without RSID.
- Everything here is receive-only. The transmit gate (callsign configured) is
  untouched and nothing in this skill keys the transmitter.
