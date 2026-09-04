"""Measured constants for this particular installation.

Everything else in this package describes the OEMZL4 in general. This module is
the one place that knows about *this* axis: the drive's DIP switch setting, the
mechanism it turns, and the scale factor measured against a ruler.

If you move this code to another rig, this is the file to change.

    >>> from parker_oemzl4.machine import connect     # doctest: +SKIP
    >>> with connect() as axis:
    ...     axis.set_speed(1, "cm/s")
    ...     axis.move_by(1, "cm")
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from turbo_pmac import PMAC

from .axis import OEMZL4Axis

#: Which motor and servo IC channel the drive is wired to.
MOTOR = 1
CHANNEL = 1

#: Microstep resolution set on the drive's SW1 DIP switches. The OEMZL4 cannot
#: report this -- it has no communications port -- so it has to be recorded.
STEPS_PER_REV = 25_000

#: Measured 4 Sep 2026: a commanded 20,000 counts moved the stage 25 mm.
COUNTS_PER_CM = 8_000.0

#: Measured independently, by counting the controller's own PFM pulses against
#: the encoder over the same open-loop output. Consistent with the above.
MICROSTEPS_PER_COUNT = 6.2682

#: Implied by the two measurements above, and all standard values, which is the
#: main reason to believe them:
ENCODER_COUNTS_PER_REV = 4_000  # 1000-line encoder, x4 quadrature decode
SCREW_PITCH_MM = 5.0  # 4000 counts/rev / 8000 counts/cm


def describe() -> str:
    """One-line summary of the measured scale, for logs and sanity checks."""
    return (f"{COUNTS_PER_CM:,.0f} counts/cm; {STEPS_PER_REV:,} steps/rev; "
            f"{ENCODER_COUNTS_PER_REV:,} encoder counts/rev; "
            f"{SCREW_PITCH_MM:g} mm/rev")


def make_axis(pmac: PMAC, motor: int = MOTOR, channel: int = CHANNEL) -> OEMZL4Axis:
    """Build a fully configured axis on an existing connection."""
    return OEMZL4Axis(pmac.motor(motor), channel=channel,
                      resolution=STEPS_PER_REV, counts_per_cm=COUNTS_PER_CM)


@contextmanager
def connect(motor: int = MOTOR, channel: int = CHANNEL) -> Iterator[OEMZL4Axis]:
    """Open the controller and yield the axis, ready to move.

    The axis is left killed on exit, whatever happens, so an exception cannot
    leave the drive energised and holding.
    """
    with PMAC() as pmac:
        axis = make_axis(pmac, motor, channel)
        try:
            yield axis
        finally:
            try:
                axis.kill()
            except Exception:  # pragma: no cover - best effort on the way out
                pass
