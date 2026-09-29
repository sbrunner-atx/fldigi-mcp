# Installing fldigi-mcp — Operator's Guide

This lets you control **fldigi** by chatting with Claude — for example
*"switch to RTTY on 20 meters"* or *"what's my frequency?"*. No programming, no
terminal.

## Where does it work?

This is a **Claude Desktop** extension. It runs in:

- ✅ **Claude Desktop** on **macOS** or **Windows** (the free app you install on
  your computer)

It does **not** work in:

- ❌ Claude in a web browser (claude.ai)
- ❌ Claude on iPhone or Android

(Extensions only run in the desktop app, because they talk to fldigi on your own
computer.)

## What you need

- **Claude Desktop** installed (from <https://claude.ai/download>).
- **fldigi** installed and running on the same computer
  (from <https://www.w1hkj.org/>), with rig control set up the usual way under
  **Configure → Config Dialog → Rig Control**: Hardware PTT for an interface such
  as a RigBlaster (serial port, RTS or DTR), or nothing for a VOX interface such as
  a SignaLink. Claude transmits by asking fldigi, so if the **T/R** button keys
  your radio, Claude can too. CAT control (Hamlib, flrig or RigCAT) is optional;
  with it, Claude can also change frequency and mode.
- Your **callsign** — only if you want to transmit. Leave it blank to listen
  only.

You do **not** need Python, `uv`, or anything technical — Claude Desktop handles
that for you.

## Step 1 — Download the extension

1. Go to the releases page:
   **<https://github.com/sbrunner-atx/fldigi-mcp/releases/latest>**
2. Under **Assets**, click **`fldigi-mcp.mcpb`** to download it.
   (Save it somewhere easy to find, like your Downloads folder.)

## Step 2 — Install it in Claude Desktop

1. Open **Claude Desktop**.
2. Open **Settings** (the Claude menu, or the gear/⚙︎ icon).
3. Click **Extensions**.
4. Click **Advanced settings**, then click **Install Extension…**.
5. Choose the **`fldigi-mcp.mcpb`** file you just downloaded.
6. Click **Install**.

> Tip: the **Install Extension…** button lives under **Advanced settings** on
> the Extensions page — that's the one spot people tend to miss.

## Step 3 — Enter your callsign

A short settings form appears:

- **Callsign** — type your callsign (e.g. `AE5VG`) to allow transmitting.
  **Leave it blank to stay receive-only** (Claude can read and tune, but can
  never key the radio).
- **Band Guidance**, **Region**, **host**, **port** — leave at the defaults
  unless fldigi runs on a *different* computer.

Click **Save**.

## Step 4 — Try it

1. Make sure **fldigi is open and running**.
2. In Claude Desktop, type: **"What's fldigi's status?"**
3. Claude replies with your current mode, frequency, and receive/transmit state.

Now try things like *"switch to BPSK31"*, *"tune to 14.070"*, or *"what have we
received?"*.

## About transmitting (please read)

- With **no callsign set**, the station is **receive-only** — nothing can put
  you on the air.
- With a callsign set, transmitting is allowed, and Claude **asks you to
  approve** each time before it keys the radio.
- **You are the licensed operator** and remain responsible for everything you
  transmit. Treat Claude as an assistant, not an autopilot.

## Running fldigi on another computer

If fldigi runs on a different PC (common in contest stations):

1. On the fldigi computer, start fldigi with
   `--xmlrpc-server-address 0.0.0.0` so it accepts connections.
2. In the extension's settings, set **fldigi host** to that computer's address
   (e.g. `192.168.1.50`).

**If the host times out (Claude Desktop and similar sandboxed clients):** the
connector can only reach `127.0.0.1`, not LAN addresses, so the correct LAN IP
fails even though `telnet` to it works. Install the small
[mcp-host-bridge](https://github.com/sbrunner-atx/mcp-host-bridge) relay on the
computer running Claude (it knows `fldigi` = 7362), then set **fldigi host =
`127.0.0.1`**:

```
mcp-host-bridge install fldigi --to 192.168.1.50
```

Keep this on a trusted home/club network — the connection is not encrypted.

## Troubleshooting

- **"Could not reach fldigi"** — make sure fldigi is open. Its remote control is
  on by default; you don't need to enable anything.
- **Nothing happens after installing** — fully quit Claude Desktop and reopen it.
- **It won't transmit** — check that you entered a callsign in the extension
  settings, and approve the prompt when Claude asks.

## Updating

When a new version is released, download the newest `fldigi-mcp.mcpb` from the
releases page and install it the same way — it replaces the old one.

## Signal hunting (optional)

There are two ways to hunt. The preferred one reads fldigi's own Signal Browser and
needs no audio setup, but it needs a patched fldigi (next section; proposed upstream,
not merged). Until the patch is in fldigi, use the sound bridge: `signal_hunt` listens
to the same receiver audio as fldigi. Where that audio is decides the setup:

| The MCP server runs... | Setting | Why |
| --- | --- | --- |
| on the Mac that hears the receiver (Claude Desktop `.mcpb`) | **Audio input device** = fldigi's input, e.g. `iMic` | Claude Desktop is not App-Sandboxed and holds the audio-input entitlement; macOS asks once for microphone permission, attributed to Claude |
| somewhere without the sound card (Cowork sandbox, a container, or fldigi on a VM via mcp-host-bridge) | run `fldigi-mcp-tap --device iMic` beside fldigi and set **Signal-hunt tap URL** = `http://127.0.0.1:7365` (or the host's address) | the tap runs where the audio is and answers over HTTP; the server never opens a device |
| anywhere, no audio at all | `signal_hunt` with `method="api"` | steps fldigi's own `search_up` and reads `get_quality`; slow and blind to mode |

### The sound bridge, step by step

**Radio on a sound card cable** (iMic, SignaLink, the radio's USB port). Two programs can
read one input device at once, so no extra driver is needed. Look up fldigi's input under
**Configure → Config Dialog → Soundcard → Devices → Capture** and put that name, or part
of it, in **Audio input device**. To hear the band on the computer, use fldigi's
**View → Rx Audio Dialog** (it plays on the **Soundcard → Alerts** device).

**Receiver audio that plays on the computer** (an SDR program, a web receiver such as a
KiwiSDR, a remote rig program such as wfview). Split it with a virtual sound card:

1. Install BlackHole 2ch (https://existential.audio/blackhole/, free).
2. In Audio MIDI Setup, **+ → Create Multi-Output Device**; tick your speakers and
   BlackHole 2ch, set **Primary Device** to the speakers, tick **Drift Correction** for
   BlackHole 2ch, and name it `Radio + speakers`.
3. Set the receiver program's output (or, for a web receiver, **System Settings → Sound →
   Output**) to `Radio + speakers`. The volume keys do not work on a Multi-Output Device.
4. Set fldigi's **Capture** to `BlackHole 2ch`, and **Audio input device** to `BlackHole`.

On Windows, VB-Audio Virtual Cable (https://vb-audio.com/Cable/) does the same: the
receiver program plays to `CABLE Input`, fldigi and **Audio input device** use
`CABLE Output`, and **Listen to this device** on `CABLE Output` (Sound control panel,
Recording tab) keeps it on your speakers. Any other splitter works as long as fldigi and
the hunt read the same audio.

## The Signal Browser (optional, needs a patched fldigi; proposed upstream, not merged)

fldigi's left-hand Signal Browser decodes up to 30 PSK, RTTY or CW stations at once
and copies signals far too weak for a spectrum to rank, but stock fldigi does not
put it on the API. The `browser` tool and `signal_hunt` with `method="browser"`
read it on a fldigi built with `patches/fldigi-4.2.13-browser-xmlrpc.patch` (see the
README for the three-line build). On stock fldigi both answer with a hint and
nothing else changes. No audio setting is involved: the browser runs inside fldigi.

If a hunt returns a `warning` about all-zero audio, the device is silent or the process lacks
microphone permission; the message says which setting to fix.
 Install the extra
(`pip install 'fldigi-mcp[hunt]'`, or the `.mcpb` runtime does it) and set
**Audio input device** to the device fldigi uses (part of its name is enough,
e.g. `iMic`). `signal_hunt` with `method="devices"` lists what it can open. macOS
asks once for microphone permission for the process that runs the server.
