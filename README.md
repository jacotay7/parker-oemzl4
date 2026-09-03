# parker-oemzl4

Notes and (eventually) control code for the **Parker Hannifin / Compumotor OEMZL4**
step motor drive.

## Short answer: talk to the Delta Tau, not to the drive

There is no way to talk to the OEMZL4 directly. It has no communications port of any
kind. In this system the **Delta Tau PMAC is the controller** — it is the thing that
holds the motion program, and the thing a host computer commands:

```
Mac  ──RS-232 / Ethernet──▶  Delta Tau PMAC  ──step + direction──▶  OEMZL4  ──▶  motor
     (ASCII command language)                 (25-pin INDEXER, 5 V opto)
```

The Delta Tau converts commanded motion into step and direction pulses (Delta Tau calls
this **PFM**, pulse frequency modulation) and feeds them to the OEMZL4's INDEXER port.
The OEMZL4 just amplifies: one microstep per rising edge, direction per the DIR line.
It has no position feedback, no state to query, and nothing to report except a single
fault contact.

So the RS-232 cable belongs on the **Delta Tau**, and any control library targets the
Delta Tau's command set — not the OEMZL4's, because the OEMZL4 does not have one.

## The OEMZL4 has no serial port

**It is not a controller.** The OEMZL4 is a packaged 4 A peak, 170 VDC bus
microstepping *drive* — a power amplifier. It has no RS-232, no RS-485, no USB, no
fieldbus, and no command language. There is nothing on it for a serial cable to talk to.

It is configured entirely by **DIP switches** and driven entirely by **step and
direction pulses** from an external indexer. Every setting — resolution, motor current,
waveform, anti-resonance, automatic standby — is a physical switch, read at power-up.

### Evidence

Three independent Parker documents agree, and none of them contains the strings
"RS-232", "baud", or "serial port" (the only hit for "serial" in 143 pages is *serial
number*, on the RMA page):

| Document | What it shows |
| --- | --- |
| [OEMZL4 Quick Reference Guide](manuals/oemzl4-quick-reference-guide-rev-b-1999.pdf) | Front panel has exactly three connectors: `INDEXER`, `MOTOR`, `AC POWER`. Configuration is SW1 (12 switches) and SW2 (6 switches, under the cover plate). |
| [ZETA Drive Installation Guide](manuals/zeta-drive-installation-guide-rev-a-1995.pdf) | The OEMZL4's full manual. Three chapters — Introduction, Installation, Troubleshooting. No communications chapter exists. |
| [OEMZL6104 Quick Reference Guide](manuals/oemzl6104-quick-reference-guide-rev-a-1999.pdf) | The sibling indexer/drive, for contrast. Its panel *does* have `COM 1` / `COM 2` with `Rx Tx GND SHLD`. The OEMZL4's does not. |

If you need serial control of a Parker stepper, the OEMZL6104 is the OEMZL4's own
drop-in counterpart — same power stage, plus a 6000-series indexer and RS-232.

## The INDEXER connector — 25-pin D, female

This is the only signal interface. Your RS-232 cable does not go here; the pins below
are opto-isolated logic inputs and an opto-isolated output, not UART lines.

| Pin | Signal | Direction | With SW1-#12 **ON** |
| --- | --- | --- | --- |
| 1 | STEP+ | in | CW+ |
| 14 | STEP− | in | CW− |
| 2 | DIR+ | in | CCW+ |
| 15 | DIR− | in | CCW− |
| 16 | SD+ (Shutdown) | in | — |
| 17 | SD− | in | — |
| 11 | RESET+ | in | — |
| 23 | RESET− | in | — |
| 9 | FLT C (fault, collector) | out | — |
| 21 | FLT E (fault, emitter) | out | — |

All other pins are unconnected. Inputs use ILD213/ILD223 optocouplers with 243 Ω
(step/dir) and 681 Ω (shutdown/reset) series resistors; step and direction are also
fed through HCPL2631 receivers, so both may be driven single-ended or differentially.

### Signal specifications

**Step input** (pin 1 / 14) — the drive advances one microstep on each **rising edge**
of a positive voltage on STEP+ with respect to STEP−.

| | |
| --- | --- |
| Input voltage | 3.5 V min (for a logic high), 5.2 V max |
| Input current | 6.5 mA min, 15 mA max |
| Pulse width | 200 ns min high, 200 ns min low |
| Max pulse rate | 2 MHz |

Note the **5.2 V maximum** — this is a 5 V interface. Do not drive it from 12 V or 24 V
logic without series resistors sized for 6.5–15 mA.

**Direction input** (pin 2 / 15) — same electrical spec as step, minus the timing.
Positive on DIR+ = clockwise; zero or negative = counterclockwise. It may change
polarity coincident with the first step pulse, so no setup delay is required.

**Shutdown input** (pin 16 / 17) — while a positive voltage is applied, motor current
is cut. Removing it restores current in the same phase relationship. 3.5 V min /
**13 V max**, 2.5–30 mA, 250 ns minimum width. Only assert it while the motor is stopped.

**Reset input** (pin 11 / 23) — equivalent to a power cycle: reloads DIP switches,
clears faults. Same 3.5–13 V / 2.5–30 mA spec, 250 ns minimum width. **Reset is not
complete until 0.7 s after the voltage is removed**, and the motor moves to the nearest
pole position. Only assert it while the motor is stopped.

**Fault output** (pin 9 / 21) — an opto-isolated transistor across FLT C (collector) and
FLT E (emitter). It **conducts when the drive is healthy** and stops conducting on any
of: no power, AC below 95 V, over 55 °C, short circuit in motor or cable, motor not
connected, interlock open, or shutdown active. Rated 30 VDC V<sub>CE</sub>, 1 V
V<sub>CE(sat)</sub>, 80 mA, 80 mW — needs an external pull-up.

### Other connectors

- **MOTOR** — 7-pin: INTERLOCK, A center tap, A+, A−, EARTH, B+, B−, B center tap,
  INTERLOCK. The interlock jumper must stay in the connector; the drive faults if
  continuity breaks. Never extend it beyond the connector.
- **AC POWER** — 95–132 VAC, 50/60 Hz, single phase. The motor case grounds through
  this connector's ground pin.

### Status LEDs

| LED | Meaning |
| --- | --- |
| POWER | Green when powered |
| STEP | Green when the drive receives a step; flashes red/green in auto test |
| OVER TEMP | Red on over-temperature fault |
| MOTOR FAULT | Red on short circuit in motor or cable, or open interlock |

## The controller: Delta Tau BC8-C0-DD2-130-00000

An 8-axis **Brick Motion Controller** built on a Turbo PMAC2 CPU — the classic Turbo
generation, not a Power PMAC, so it speaks the well-documented ASCII on-line command
language (`#1J+`, `#1J/`, `P1=1000`, `I130=...`, `OPEN PROG 1`).

Decoded from the Hardware Reference's model-number table:

| Field | Code | Meaning |
| --- | --- | --- |
| Axes | `BC8` | Eight axes |
| CPU | `C0` | 80 MHz Turbo PMAC2, 256K×24 SRAM, 1 MB flash |
| Axis 1-4 / 5-8 output | `D` / `D2` | Dual true-DAC analog, 18-bit, 12-24 V flags |
| Digital I/O | `1` | Expanded: +16 inputs, +8 outputs, 0.5 A 24 VDC |
| Analog I/O | `3` | Two 16-bit analog inputs |
| Special feedback / serial encoder / MACRO | `00` `0` `0` | None |
| Communications | `0` | **No options — default** |

### Use Ethernet, not the USB cable

The final `0` means **this unit has no RS-232 port** — that is an ordering option
(`R`, `E`, `N`, `T`) this unit was not built with. It has exactly two host interfaces:
**X13 USB 2.0** and **X14 RJ45 Ethernet, 100 Base-T**.

The USB port is a dead end on a Mac. Delta Tau's USB is a vendor-specific device, not
USB-CDC, so it presents no serial port and needs their `PMACUSB.SYS` kernel driver —
which the ACC-54E manual scopes to "Windows 98, Windows ME, Windows 2000 and in the
future Windows XP". Nothing exists for macOS. Moving that cable to the Mac will not
produce a `/dev/cu.*` node.

**Ethernet is fully documented and needs no driver at all.** Per the ACC-54E manual,
the controller listens on **UDP or TCP port 1025**, and every exchange is one
`ETHERNETCMD` packet:

```c
typedef struct tagEthernetCmd {
    BYTE RequestType;    // VR_UPLOAD 0xC0 (read) / VR_DOWNLOAD 0x40 (write)
    BYTE Request;        // VR_PMAC_GETRESPONSE 0xBF, VR_PMAC_SENDLINE 0xB0,
                         // VR_PMAC_GETLINE 0xB1, VR_PMAC_FLUSH 0xB3, ...
    WORD wValue;         // network byte order
    WORD wIndex;
    WORD wLength;
    BYTE bData[1492];
} ETHERNETCMD;
```

`VR_PMAC_GETRESPONSE` (0xBF) sends a command string and returns the reply, reading up
to an `<ACK>` or `<LF>`. That is the whole request/response cycle a library needs, and
it is implementable in pure Python with the standard `socket` module — no drivers, no
kernel extensions, no App Store detour. Delta Tau's factory default address is
**192.6.94.5** (worth confirming against however this unit was commissioned).

That makes this a materially easier target than the AR-04AE, which needed a Prolific
kext approved by hand before it would enumerate.

### How the Brick reaches the OEMZL4

You said the Parker is on **AMP 1 / ENC 1**. The Brick provides pulse and direction
outputs as standard on every channel: `I7mn0 = 8` selects internal pulse-and-direction
and `I7mn6` switches the channel's C output to PFM. The Hardware Reference states these
step and direction outputs are **RS-422 compatible** — which is exactly what the
OEMZL4's HCPL2631 differential receivers on STEP± and DIR± are designed to accept, so
the two are a native electrical match.

`ENC 1` suggests an encoder is closing the loop in the Brick, which the OEMZL4 alone
cannot do — it has no feedback input. Worth confirming before changing anything, since
it means the axis may be configured as a closed-loop stepper rather than open-loop.

## Manuals

Nine PDFs in two sets under [manuals/](manuals/), indexed at
[manuals/README.md](manuals/README.md):

- [manuals/delta-tau-brick/](manuals/delta-tau-brick/) — the Brick Controller Hardware
  Reference, the Turbo PMAC User Manual and Software Reference (the full command and
  I-variable dictionary), and the ACC-54E manual that documents the Ethernet/USB wire
  protocol. Recovered from the Internet Archive; `deltatau.com` no longer serves them.
- [manuals/parker-oemzl4/](manuals/parker-oemzl4/) — the OEMZL4 Quick Reference, the
  ZETA Drive Installation Guide that is its actual manual, the EMC guide, and the
  RS-232-equipped OEMZL6104 siblings for comparison.

Each index gives part numbers, revisions and dates, states which documents the
manufacturers consider applicable to these exact models, and records what was
downloaded and discarded as belonging to a different product.

## Next step

Confirm the Brick's IP address and that it answers on port 1025, then build the library
against `VR_PMAC_GETRESPONSE`. Before commanding motion, read the axis's existing
configuration out of the controller (`I7mn0`, `I7mn6`, `Ixx30`, and the Ixx8x feedback
setup) rather than assuming it — whatever commissioned this system already encoded the
step resolution, ramps and any encoder loop, and that configuration is worth preserving.
