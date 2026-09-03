"""Facts about the Parker OEMZL4 step motor drive.

The OEMZL4 has no communications port: no RS-232, no fieldbus, no command
language. It is configured by DIP switches read at power-up and driven by step
and direction pulses on a 25-pin D connector. So this module is reference data
and validation, not a protocol -- there is nothing to talk to.

Sources, all in ``manuals/parker-oemzl4/``: the OEMZL4 Quick Reference Guide
(88-018139-01B) for switch tables and pinout, and the ZETA Drive Installation
Guide (88-014027-01A), which is the OEMZL4's full manual, for signal
specifications.
"""

from __future__ import annotations

from dataclasses import dataclass

# -- The 25-pin INDEXER connector -----------------------------------------

#: Pin assignments. Every other pin is unconnected.
PINOUT = {
    1: "STEP+",
    14: "STEP-",
    2: "DIR+",
    15: "DIR-",
    16: "SD+",
    17: "SD-",
    11: "RESET+",
    23: "RESET-",
    9: "FLT C",
    21: "FLT E",
}

#: With SW1-#12 ON the step/direction pair becomes clockwise/counterclockwise.
PINOUT_CW_CCW = {1: "CW+", 14: "CW-", 2: "CCW+", 15: "CCW-"}


@dataclass(frozen=True)
class SignalSpec:
    """Electrical limits for one opto-isolated input."""

    name: str
    v_min: float
    v_max: float
    i_min_ma: float
    i_max_ma: float
    min_pulse_ns: int | None = None

    def accepts(self, volts: float) -> bool:
        return self.v_min <= volts <= self.v_max


#: A step is registered on the rising edge of STEP+ with respect to STEP-.
STEP = SignalSpec("step", 3.5, 5.2, 6.5, 15.0, min_pulse_ns=200)
DIRECTION = SignalSpec("direction", 3.5, 5.2, 6.5, 15.0)
SHUTDOWN = SignalSpec("shutdown", 3.5, 13.0, 2.5, 30.0, min_pulse_ns=250)
RESET = SignalSpec("reset", 3.5, 13.0, 2.5, 30.0, min_pulse_ns=250)

#: Maximum step rate the drive will accept.
MAX_STEP_RATE_HZ = 2_000_000

#: Minimum high and low time of a step pulse.
MIN_PULSE_NS = 200

#: A reset is not complete until this long after the input is released.
RESET_SETTLING_S = 0.7

#: Fault output ratings: an opto-isolated transistor across FLT C and FLT E
#: that **conducts while the drive is healthy**.
FAULT_VCE_MAX_V = 30.0
FAULT_CURRENT_MAX_MA = 80.0

#: Every condition that opens the fault contact.
FAULT_CAUSES = (
    "no power applied",
    "AC line below 95 VAC",
    "drive temperature above 55 C",
    "short circuit in motor or motor cable",
    "motor not connected",
    "interlock continuity broken",
    "shutdown input active",
)

# -- DIP switches ----------------------------------------------------------

#: Microstep resolutions in steps per revolution, selected by SW1-#7..#10.
#: The drive reads these only at power-up.
RESOLUTIONS = (
    200, 400, 1000, 2000, 5000, 10000, 12800, 18000,
    20000, 21600, 25000, 25400, 25600, 36000, 50000, 50800,
)

#: Motor current settings in amps, selected by SW1-#1..#5.
CURRENTS = (
    0.14, 0.26, 0.39, 0.51, 0.64, 0.76, 0.89, 1.01,
    1.14, 1.26, 1.38, 1.51, 1.63, 1.76, 1.88, 2.01,
    2.14, 2.26, 2.38, 2.51, 2.63, 2.76, 2.88, 3.01,
    3.13, 3.26, 3.38, 3.50, 3.63, 3.75, 3.88, 4.00,
)

#: Supply. The OEMZL4 is the 95-132 VAC part -- do not use the ZETA4-240
#: manual's power figures, which cover the 95-264 VAC variant.
SUPPLY_VOLTAGE_RANGE = (95.0, 132.0)


def steps_per_rev(switch_code: int) -> int:
    """Resolution for a SW1-#7..#10 code, 0-15."""
    if not 0 <= switch_code < len(RESOLUTIONS):
        raise ValueError(f"resolution code out of range: {switch_code}")
    return RESOLUTIONS[switch_code]


def current_amps(switch_code: int) -> float:
    """Motor current for a SW1-#1..#5 code, 0-31."""
    if not 0 <= switch_code < len(CURRENTS):
        raise ValueError(f"current code out of range: {switch_code}")
    return CURRENTS[switch_code]


def max_speed_rps(resolution: int) -> float:
    """Top speed in revolutions per second at a given resolution.

    Limited by the drive's 2 MHz maximum step rate, not by the motor.
    """
    if resolution <= 0:
        raise ValueError("resolution must be positive")
    return MAX_STEP_RATE_HZ / resolution


def check_step_rate(rate_hz: float) -> None:
    """Raise if a commanded step rate exceeds what the drive accepts."""
    if rate_hz > MAX_STEP_RATE_HZ:
        raise ValueError(
            f"{rate_hz:,.0f} Hz exceeds the OEMZL4's {MAX_STEP_RATE_HZ:,} Hz limit")
