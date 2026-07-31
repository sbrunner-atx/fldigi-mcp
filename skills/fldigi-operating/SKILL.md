---
name: fldigi-operating
description: >
  Operating discipline for driving fldigi via fldigi-mcp: keying the
  transmitter, returning to receive instantly after an over, and polling the
  RX buffer so no answer is missed. Use whenever conducting live QSOs,
  running a CQ loop, or any operation that alternates transmit and receive
  (contest exchanges, keyboard-to-keyboard QSOs, beacon-style calling).
  Field-proven during ARRL Field Day 2026 (BPSK31; example callsigns anonymized).
---

# Operating fldigi: TX/RX handoff and RX polling

## The one rule that matters most

**Never poll the TX buffer to decide when to stop transmitting.** fldigi
never auto-stops on an empty buffer — it holds PTT and sends idle until
something explicitly returns it to receive. Detecting "buffer empty" from
outside always lags, and you transmit idle carrier on top of the station
answering you.

Instead, end every over with the inline return-to-receive control character
`^r`. The `transmit → send` operation does this for you.

## Transmitting an over

```
transmit → send "<over text>\n"   (return_to_rx=true, the default)
```

One call: clears the TX buffer, appends `^r`, keys the radio. When the modem
reaches `^r` — the exact sample the last real character finishes — fldigi
drops to RX instantly. No polling, no lag, no lingering carrier.

- End each message with a real newline character (`\n`) so the receiving
  station's display advances a line. Do **not** use the two-character string
  `^n` — it is transmitted literally as caret-n.
- If an over must be built incrementally with `text → add_tx`, the **last**
  `add_tx` must end in `^r` before `transmit → tx`, and nothing may be added
  after it.

### The three ways to stop, and when to use each

| Operation | Behavior | Use for |
|---|---|---|
| `^r` in stream (via `send`) | Graceful auto-return the moment the over ends | Every normal over |
| `transmit → abort` | Immediate stop, discards queued text | Panic button: caller came back early, wrong message, operator says stop |
| `transmit → rx` | Returns to RX only **after** the buffer drains | Almost never — it is slow and is *not* the stop button |

## Waiting for TX to finish

After `send`, poll `controls → get_trx_status` until it returns `"rx"`.
A BPSK31 over of 2–4 short lines takes roughly 15–30 seconds; poll at a
relaxed interval rather than hammering the API.

## Listening: RX buffer discipline

Track the RX stream by position, reading only deltas:

1. `text → rx_length` → current end position.
2. `text → read` from your last known position to the new length.
3. Save the new position.

**Rules learned the hard way:**

- **fldigi never echoes your own TX into the RX buffer.** Every character in
  RX came from an external station. If your own callsign appears in RX,
  someone is transmitting it — i.e., they are calling you. Always pursue it.
  Do not build any "dismiss as own echo" logic; it will make you ignore
  callers.
- **Restart detection:** if `rx_length` comes back *smaller* than your last
  position, fldigi was restarted and the buffer reset. Re-baseline: read
  from 0 (or just adopt the new length as your position) and continue.
- **Listen window:** after an over ends (status returns `"rx"`), listen
  ~10 seconds — one or two `rx_length` polls — before concluding nobody
  answered. PSK31 operators type slowly; the reply often starts several
  seconds after your carrier drops.
- Partial decodes are normal. A caller's message may arrive across several
  reads with garbage interleaved. Keep reading until you have a clean
  callsign before responding; if the buffer goes quiet and you still don't
  have one, ask for a repeat ("AGN").

## A complete CQ loop (reference pattern)

```
loop:
  transmit → send "CQ CQ de <MYCALL> <MYCALL> pse k\n"
  poll controls → get_trx_status until "rx"
  listen ~10 s (1–2 polls of text → rx_length)
  if new RX text contains a plausible callsign:
      work the station (see contest-operating skill in n3fjp-mcp
      for the full exchange state machine)
  else:
      goto loop
```

Validate a decoded callsign against the standard pattern
(`[A-Z0-9]{1,3}[0-9][A-Z]{1,3}` plus optional portable suffix) before
sending a directed reply — QRM garbage can look like a call fragment.

## Connectivity note

fldigi's XML-RPC default port is **7362**. If the connector is configured
for a different port (e.g., 7372), that usually means a localhost→remote
forwarder is intended — check `FLDIGI_PORT` before concluding fldigi is
down. The `diagnostics` tool checks reachability without needing fldigi.
