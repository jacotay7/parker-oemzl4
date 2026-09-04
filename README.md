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

## Commissioning (4 Sep 2026)

The axis now runs under closed-loop control. Four faults were found, **all of
them configuration** -- the wiring was correct throughout.

### 1. `I102` pointed at the wrong register

This was the root cause, and the reason no pulses ever reached the drive.

Each PMAC2-style servo IC channel occupies eight addresses: the **A** output at
base+2, the **C** output at base+4. PFM is emitted from the **C** register only.
`I102` was `$078002` -- channel 1's *A* output, the DAC/PWM register, which is
the Turbo PMAC2 factory default. The servo wrote a perfectly correct command
there every cycle, the PFM circuit read the untouched C register, and not one
pulse was ever emitted. Nothing reports this: the command register looks right,
the status is clean, and the axis simply never moves.

`I102 = $078004` fixed it. `c_output_address()` computes this per channel, and
`check_configuration()` now rejects any other address.

It also explains the original runaway. With `I7016=0` all three outputs are
PWM, so C emitted a carrier and the motor ran continuously; switching C to PFM
silenced it, because C's register was never written.

### 2. `I7016` left the C output as a PWM carrier

`0` -> `2`. A PWM carrier is a constant-rate pulse train to a stepper drive.

### 3. Amplifier fault polarity, and a latch

`I124` bit 23 was set for a drive whose fault opto conducts *while faulted*; the
OEMZL4's conducts while **healthy**. `$1` -> `$800001`. Separately, the fault
status bit **latches** -- `kill` does not clear it, only a successful re-enable.

### 4. Inverted feedback polarity

`+` output produced `-` counts, which would have made the closed loop a
positive-feedback runaway. `I7010: 7` -> `3` -- the SRM's own advice, *"simply
change to the other option (e.g. from 7 to 3)"*.

### Measured behaviour

| | |
| --- | --- |
| Holding | 0.00 counts drift |
| 100 / 500 / 3000 count moves | exact, following error 0 |
| Usable jog speed | up to `I122=8` (8000 counts/msec setting) |
| Achieved rate | ~5000 counts/s on a 10000-count move |
| Limit | acceleration, not velocity |

One trap worth recording: a *tightened* `I111=2000` fatal-following-error limit
tripped instantly on the acceleration transient, which looks exactly like a
motor stall. At `I111=16000` the same moves run with a peak following error of
**1**. A protection set too tight is indistinguishable from the fault it guards
against.

### Working configuration (not yet saved)

| Variable | Default | Now | Why |
| --- | --- | --- | --- |
| `I102` | `$078002` | `$078004` | C output -- the only register PFM reads |
| `I7016` | 0 | 2 | C output PFM, not a PWM carrier |
| `I7010` | 7 | 3 | feedback direction sense |
| `I124` | `$1` | `$800001` | amplifier fault polarity |
| `I111` | 32000 | 16000 | fatal following error |
| `I119` | 0.015625 | 0.0625 | jog acceleration |
| `I122` | 32 | 8 | jog speed |
| `I113`/`I114` | 0 (off) | +/-30000 counts | travel envelope |

**A controller reset restores the defaults, which include the runaway.** Run
`SAVE` once the configuration is trusted.

## Saved, and verified across a reset

The working configuration is now in flash. Verified properly, by resetting the
controller with `$$$` and reading the values back as they loaded:

```
I102 $78004   I7016 2   I7010 3   I124 $800001
I111 16000    I119 0.0625   I122 8
drift after reset: +0.00 counts
```

**The power-up runaway is gone permanently.** A read-back before the reset would
only have proved what was in RAM, which is not the thing that matters.

Software travel limits were deliberately left **disabled** (`I113=I114=0`, the
factory state) rather than persisted. The envelope used during commissioning was
centred on an arbitrary position; saved, it would have blocked legitimate moves
later for no discoverable reason. Set real ones once the true travel is known.

**Position is relative to each power-up.** The encoder is incremental and the
counter zeroes on reset -- after `$$$` the axis read `0.47` rather than the
`211,185` it held before. Absolute positioning needs a homing routine against a
reference switch; none is configured.

## Scale — measured

Three independent measurements, which agree:

| Quantity | Value | How |
| --- | --- | --- |
| **Counts per cm** | **8,000** | 20,000 counts moved the stage 25 mm |
| Motor microsteps per encoder count | 6.2682 | counting the controller's own PFM pulses against the encoder |
| Encoder | 4,000 counts/rev | implied — a 1000-line encoder with x4 quadrature |
| Drive resolution | 25,000 steps/rev | implied: 4,000 x 6.2682 = 25,073, and 25,000 is a real DIP setting |
| Screw pitch | 5 mm/rev | implied: 4,000 counts/rev / 8,000 counts/cm |

The scale factor came from a ruler; the microstep ratio came from the
controller's own hardware counter. They were taken separately and land on
standard values for a 1000-line encoder and a 5 mm leadscrew, which is the main
reason to trust them. `tests/test_units.py` asserts they stay consistent.

Verified on the hardware: a commanded `move_by(-1.0, "cm")` moved **-9.990 mm**,
and `move_by(+1.0, "cm")` at 1 cm/s moved **+9.997 mm** and returned to the same
position. About 0.1%.

## Usage

```python
from parker_oemzl4.machine import connect

with connect() as axis:
    axis.set_speed(1, "cm/s")
    axis.move_by(1, "cm")           # relative move
    print(axis.position("mm"))
```

`connect()` opens the controller, applies this installation's measured
constants, and kills the axis on the way out whatever happens, so an exception
cannot leave the drive energised. All the machine-specific numbers live in
[parker_oemzl4/machine.py](parker_oemzl4/machine.py) — the one file to change
for a different rig.

Units are free-form: `"cm"`, `"mm"`, `"m"`, `"um"`, `"in"`, and rates like
`"cm/s"` or `"mm/min"`. Speeds are checked against the drive's 2 MHz step-rate
ceiling, which at 25,000 steps/rev works out to 80 rev/s, or **40 cm/s**.

For raw work, `axis.move_counts()` needs no scale factor, and the controller
itself is available through `turbo_pmac` with no knowledge of this drive at all.

## Known limitations

- **No absolute position.** The encoder is incremental and its counter zeroes on
  every controller reset, so position is relative to power-up. `move_by` is
  exact; `move_to` means "from wherever it was at power-on". Absolute
  positioning needs a homing routine against a reference switch, and none is
  configured. Whether a home or limit switch is even wired to the Brick's `J4`
  connector is not yet established.
- **No travel limits.** Hardware overtravel inputs are not known to be wired,
  and the software limits `I113`/`I114` are disabled. Nothing stops a commanded
  move from driving into a hard stop. Set real ones once the travel is measured.
- **Short moves do not reach the commanded speed.** A 1 cm move at 1 cm/s
  averages about 0.55 cm/s, because acceleration and deceleration dominate at
  that distance. Raise `I119` if that matters, gently — it is a stepper.
