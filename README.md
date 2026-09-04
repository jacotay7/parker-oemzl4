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

### Talking to it: USB works, Ethernet does not

The final `0` in the model number means **no RS-232 port** was fitted, leaving
**X13 USB 2.0** and **X14 RJ45 Ethernet**. In practice only USB is usable here.

**Ethernet is silent.** The link negotiates (100baseTX full duplex), but the
controller answers nothing: no reply on Delta Tau's factory default 192.6.94.5,
no ARP response anywhere on 192.6.94.0/24, and not one unsolicited packet in
minutes of listening. Its stored IP is unknown and it announces nothing, so
there is no way to find it by listening. Not worth pursuing while USB works.

**USB works, with no Delta Tau driver.** The controller enumerates as:

```
0x0aa2:0x0007  Delta Tau Data Systems, Inc.  "ACC54E USB2"
  interface 0, class 255 (vendor-specific)
  bulk 0x01 OUT / 0x81 IN (64B);  0x02, 0x04 OUT / 0x86, 0x88 IN (512B)
```

Interface class 255 means macOS has no driver for it and never claims it, which
leaves it free for `libusb`. Delta Tau's `PMACUSB.SYS` is only needed by their
own Windows software, not by the protocol.

The bulk endpoints are a red herring. The `ETHERNETCMD` struct in the ACC-54E
manual -- `RequestType`, `Request`, `wValue`, `wIndex`, `wLength` -- is exactly a
USB control setup packet, because Delta Tau reused USB's framing for their
Ethernet protocol. Over USB these are **control transfers**:

```
SENDLINE  bmRequestType 0x40, bRequest 0xB0, data = command + "\r"
GETLINE   bmRequestType 0xC0, bRequest 0xB1, returns the reply
```

Three behaviours are not in any manual and cost real time to find:

1. **`GETLINE` returns a NUL byte when nothing is ready.** It does not block and
   does not return a zero-length transfer, so the caller must poll for data.
2. **The `<ACK>` that terminates a reply arrives on a later read than the reply
   text.** Stop reading early and the ACK stays queued, where it is mistaken for
   the next command's reply -- every command after it returns the previous
   command's answer, with the lag growing.
3. **Never issue `GETLINE` while no command is pending.** Draining the queue
   before sending wedges the device: every subsequent reply comes back empty.
   Keep sync by ignoring a bare leftover `<ACK>` instead.

Setup, once:

```bash
brew install libusb
python3 -m pip install -e .

python3 -m turbo_pmac probe            # identify and survey
python3 -m turbo_pmac status 1         # decode motor status bits
python3 -m turbo_pmac send "#1P" I130  # raw queries
python3 -m turbo_pmac estop            # disable PLCs, then kill all motors
```

### Controller state as found (3 Sep 2026)

Read over USB with `python3 -m turbo_pmac probe`, before any change was made:

| Query | Value | Meaning |
| --- | --- | --- |
| `VERSION` | `1.947` | Turbo PMAC firmware |
| `TYPE` | `TURBO2, X4` | Turbo PMAC2 |
| `#1?` | `850000000000` | activated, **amplifier disabled, open loop** |
| `#1P` / `#1V` / `#1F` | `-5797.53` / `0` / `0` | stopped, no following error |
| `I5` | `0` | **all PLC programs disabled** |
| `I100` / `I101` | `1` / `0` | motor 1 active, commutation off |
| `I102` | `$78002` | output = servo IC 0, channel 1, **C register** |
| `I103` / `I104` | `$3501` / `$3501` | feedback from encoder conversion table |
| `I111` / `I130` / `I169` | `32000` / `2000` / `20480` | fatal following error, gain, output limit |
| `I7010` | `7` | channel 1 encoder decode |
| `I7016` | `0` | **A & B PWM, C PWM** |
| `I7002` / `I7004` | `3` / `15` | PFM clock divider, pulse width |

**The controller is running factory defaults.** `I111=32000`, `I130=2000`,
`I169=20480`, `I7016=0`, `I102=$78002` and `I103/I104=$3501` are all the Turbo
PMAC2 power-on values for motor 1, and `I5=0` means no PLC is running. There is
no commissioned machine configuration on this unit -- nothing was preserved to
lose, and nothing here was set up for this stepper axis.

**That explains the runaway.** Motor 1 commands `$78002`, the channel 1 C
output, but `I7016=0` leaves C in **PWM** mode. PWM is a continuous carrier, not
pulses proportional to commanded velocity. Fed into the OEMZL4's STEP input it
reads as an endless, constant-rate step train, so the motor runs continuously
regardless of what motion is commanded. For step and direction the C output must
be PFM, which is `I7016 = 2` (A & B PWM) or `3` (A & B DAC).

This is a hypothesis consistent with every reading taken so far, not yet a
confirmed fix -- it has not been tested against the drive.

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

## Packages

Two packages, deliberately separate so the controller half is reusable on any
Turbo PMAC:

### `turbo_pmac` — the controller library

Knows nothing about the OEMZL4, or about any particular machine.

| Module | Contents |
| --- | --- |
| `transport.py` | `USBTransport` (libusb, verified) and `EthernetTransport` (untested) |
| `protocol.py` | `ETHERNETCMD` framing, `VR_*` request codes, control characters |
| `controller.py` | `PMAC`: command dispatch, variables, `emergency_stop()` |
| `motor.py` | `Motor`: position, velocity, status, kill, jog, home |
| `status.py` | `MotorStatus`, decoding all 39 status bits from the SRM tables |
| `response.py` | Reply parsing: hex `$` values, status words, error codes |
| `errors.py` | Typed exceptions, with the manual's `ERRnnn` meanings |
| `testing.py` | `FakeTransport`, reproducing the real framing quirks |

```python
from turbo_pmac import PMAC

with PMAC() as pmac:
    print(pmac.version)                       # '1.947'
    motor = pmac.motor(1)
    print(motor.status.summary())             # 'killed (outputs disabled)'
    print(motor.position, motor.following_error)
```

### `parker_oemzl4` — the drive

Reference data from the manuals (pinout, signal specs, DIP switch tables) plus
`OEMZL4Axis`, which adds the drive's limits to a controller motor. Because the
drive cannot be asked anything, its resolution has to be told to the library.

```python
from turbo_pmac import PMAC
from parker_oemzl4 import OEMZL4Axis

with PMAC() as pmac:
    axis = OEMZL4Axis(pmac.motor(1), channel=1, resolution=25000)
    print(axis.check_configuration().report())
    axis.enable()        # refuses while the channel is still in PWM mode
```

`check_configuration()` is read-only and is what caught the fault documented
above. `enable()` will not run an axis that fails it.

```bash
python3 -m pytest        # 47 tests, no hardware required
```

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

## Commissioning progress (4 Sep 2026)

Working, verified on hardware:

- **The runaway is fixed.** `I7016: 0 -> 2` switched channel 1's C output from a
  PWM carrier to PFM. The axis was creeping at **-725 counts/s while the motor
  was killed** -- the carrier was turning it in hardware, outside the servo loop
  entirely. After the change: 0.000 counts of drift.
- **The amplifier fault was configuration, not wiring.** Two separate things:
  `I124` bit 23 had the wrong fault polarity for a drive whose fault opto
  conducts while healthy (`$1` -> `$800001`), and the fault status bit is
  *latched* -- `kill` does not clear it, only a successful re-enable does.
- **The axis now closes the loop and holds position**: `amplifier_enabled`,
  `in_position`, `desired_velocity_zero`, following error 0.

### Blocked: PFM pulses are gated in hardware

Commanded moves produce no motion at all. The controller side is provably
correct -- the C output command register `Y:$078002` tracks the commanded
output exactly:

| Command | `Y:$078002` | Motion |
| --- | --- | --- |
| `#1O0` | 0 | none |
| `#1O5` | 262,144 | none |
| `#1O20` | 1,048,576 | none |
| `#1O-20` | -1,048,576 | none |

So the pulses are commanded and then blocked. Per the Brick Hardware
Reference, step and direction exist **only on the X connectors**, and are gated:

> Pin 8 | Stepper Enable #n | **Short pin 8 to pin 4 (5V) to enable stepper
> output for channel #n**

The `AMP1-AMP8` connectors carry no pulse output whatsoever -- only DAC A/B,
the amplifier-enable relay, and the amplifier-fault input.

| Brick X1 pin | Signal | OEMZL4 25-pin |
| --- | --- | --- |
| 6 | PUL1+ | 1 (STEP+) |
| 14 | PUL1- | 14 (STEP-) |
| 5 | DIR1+ | 2 (DIR+) |
| 13 | DIR1- | 15 (DIR-) |
| **8 to 4** | **Stepper Enable, shorted to +5 V** | -- |

### Not saved

None of these changes are persisted. **A controller reset restores `I7016=0`
and the continuous drift returns.** Run `SAVE` only once the configuration is
known good.

| Variable | As found | Now | Why |
| --- | --- | --- | --- |
| `I7016` | 0 | 2 | C output PFM, not a PWM carrier |
| `I124` | `$1` | `$800001` | amplifier fault polarity |
| `I111` | 32000 | 2000 | trip faster on a runaway |
| `I122` | 32 | 1 | slow jog for commissioning |
| `I113`/`I114` | 0 (disabled) | +/-1500 counts | temporary travel envelope |

### Still to do

Physical units. Converting counts to cm needs one measured move -- command a
known number of counts, measure the actual travel, and divide. That number
cannot be derived from either manual.

## Next step

The drive is currently disconnected, and the controller is in a safe state:
motor 1 is activated but killed, with outputs disabled and the loop open.

Before reconnecting the OEMZL4, `I7016` must be changed from `0` to `2` or `3`
so the channel's C output emits PFM instead of a PWM carrier. Nothing else on
this controller is configured, so that one change is necessary but almost
certainly not sufficient.

Two things worth doing first:

1. **Look for the original configuration.** The PC that had the USB cable may
   hold a Pewin project or a saved `.pmc` download from whoever commissioned
   this. Restoring that beats reconstructing it.
2. **Decide whether this axis is open or closed loop.** `ENC 1` has a live
   encoder (the conversion table entry reads a real count), and `I103`/`I104`
   point at it, but those are also the power-on defaults, so they prove nothing
   about intent.

Do not `SAVE` while experimenting. Without it every change is lost on reset,
which is the safer state until the configuration is known good.
