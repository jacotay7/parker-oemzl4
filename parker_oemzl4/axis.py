"""An OEMZL4 driven by one channel of a Turbo PMAC.

The drive is deaf and mute: it accepts step and direction pulses and reports
nothing but a single fault contact. Everything you can ask or command goes to
the controller, so this class wraps a :class:`turbo_pmac.Motor` and adds the
drive's limits, the checks its wiring implies, and physical units.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from turbo_pmac import Motor
from turbo_pmac.response import as_int

from . import drive, units

#: I7mn6 settings whose C output is PFM rather than a PWM carrier.
PFM_OUTPUT_MODES = (2, 3)

#: Ixx22 (jog speed) is in counts per millisecond.
_JOG_SPEED_IVAR = 22


def c_output_address(channel: int) -> int:
    """Address of a channel's C output register, which carries PFM.

    Each PMAC2-style servo IC channel occupies eight addresses; the A output
    sits at base+2 and the C output at base+4. Channels 1-4 are on servo IC 0
    at $078000, channels 5-8 on servo IC 1 at $078100.

    Getting this wrong is silent and total: the servo writes a perfectly
    correct command to the A register, the PFM circuit reads the untouched C
    register, and not one pulse is ever emitted.
    """
    if not 1 <= channel <= 8:
        raise ValueError(f"channel out of range: {channel}")
    servo_ic, index = divmod(channel - 1, 4)
    return 0x078000 + servo_ic * 0x100 + index * 8 + 4


@dataclass(frozen=True)
class ConfigCheck:
    """Result of :meth:`OEMZL4Axis.check_configuration`."""

    ok: bool
    problems: tuple[str, ...]
    notes: tuple[str, ...]

    def __bool__(self) -> bool:
        return self.ok

    def report(self) -> str:
        lines = ["configuration OK" if self.ok else "configuration NOT safe to run"]
        lines += [f"  problem: {p}" for p in self.problems]
        lines += [f"  note:    {n}" for n in self.notes]
        return "\n".join(lines)


class OEMZL4Axis:
    """A Parker OEMZL4 on a Turbo PMAC channel.

    :param motor: the controller motor commanding this drive.
    :param channel: the servo IC channel wired to the drive, 1-8.
    :param resolution: steps per revolution set on the drive's DIP switches.
        The drive cannot be asked, so it must be told.
    :param counts_per_cm: encoder counts per centimetre of travel. Measure it
        once with ``tools/calibrate.py``; it cannot be derived from a manual.
    """

    def __init__(self, motor: Motor, channel: int = 1,
                 resolution: int | None = None,
                 counts_per_cm: float | None = None):
        if not 1 <= channel <= 8:
            raise ValueError(f"channel out of range: {channel}")
        self.motor = motor
        self.channel = channel
        self.resolution = resolution
        self.counts_per_cm = counts_per_cm

    def __repr__(self) -> str:
        return f"<OEMZL4Axis motor #{self.motor.number} channel {self.channel}>"

    # -- servo IC addressing ----------------------------------------------

    @property
    def _servo_ic(self) -> int:
        return 0 if self.channel <= 4 else 1

    @property
    def _channel_in_ic(self) -> int:
        return self.channel if self.channel <= 4 else self.channel - 4

    def _i7var(self, param: int) -> str:
        return f"I7{self._servo_ic}{self._channel_in_ic}{param}"

    @property
    def output_mode(self) -> int:
        """I7mn6: 0/1 leave the C output as PWM, 2/3 make it PFM."""
        return as_int(self.motor.pmac.get(self._i7var(6)))

    @property
    def encoder_decode(self) -> int:
        """I7mn0: how the channel decodes its feedback input."""
        return as_int(self.motor.pmac.get(self._i7var(0)))

    # -- validation --------------------------------------------------------

    def check_configuration(self) -> ConfigCheck:
        """Check the controller is set up to drive this step/direction amplifier.

        Read-only. Does not move the axis and changes nothing.
        """
        problems: list[str] = []
        notes: list[str] = []

        mode = self.output_mode
        if mode not in PFM_OUTPUT_MODES:
            problems.append(
                f"{self._i7var(6)}={mode} leaves the channel's C output in PWM mode. "
                "PWM is a continuous carrier, so the drive sees an endless "
                "constant-rate step train and runs continuously regardless of what "
                "is commanded. Set it to 2 (A/B PWM) or 3 (A/B DAC).")

        expected = c_output_address(self.channel)
        actual = self.motor.output_address
        if actual != expected:
            problems.append(
                f"I{self.motor.number}02=${actual:X} does not point at channel "
                f"{self.channel}'s C output (${expected:X}). PFM is emitted from the "
                "C register only; commanding any other register produces no pulses "
                "at all, silently.")

        status = self.motor.status
        if not status.activated:
            notes.append(f"motor is deactivated (I{self.motor.number}00=0)")
        if status.faulted:
            notes.append(f"motor reports a fault: {', '.join(status.active_flags())}")
        if self.counts_per_cm is None:
            notes.append("counts_per_cm is unset, so physical units are unavailable")

        return ConfigCheck(not problems, tuple(problems), tuple(notes))

    # -- speed limits ------------------------------------------------------

    def max_speed_rps(self) -> float:
        """Top speed in rev/s, set by the drive's 2 MHz step-rate ceiling."""
        if self.resolution is None:
            raise ValueError("resolution is unknown; read the drive's DIP switches")
        return drive.max_speed_rps(self.resolution)

    def check_speed_rps(self, rps: float) -> None:
        if self.resolution is None:
            raise ValueError("resolution is unknown; read the drive's DIP switches")
        drive.check_step_rate(abs(rps) * self.resolution)

    # -- units -------------------------------------------------------------

    def _require_scale(self) -> float:
        if self.counts_per_cm is None:
            raise ValueError(
                "counts_per_cm is unknown. Measure it once with "
                "tools/calibrate.py -- it cannot be derived from the manuals.")
        return self.counts_per_cm

    def to_counts(self, distance: float, unit: str = "cm") -> float:
        return units.length_to_counts(distance, unit, self._require_scale())

    def to_length(self, counts: float, unit: str = "cm") -> float:
        return units.counts_to_length(counts, unit, self._require_scale())

    @property
    def position_counts(self) -> float:
        return self.motor.position

    def position(self, unit: str = "cm") -> float:
        """Present position in physical units."""
        return self.to_length(self.motor.position, unit)

    @property
    def speed(self) -> float:
        """Configured jog speed, in counts per millisecond (Ixx22)."""
        return float(self.motor.ivar(_JOG_SPEED_IVAR))

    def set_speed(self, value: float, unit: str = "cm/s") -> float:
        """Set the jog speed. Returns the value written to Ixx22."""
        per_msec = units.speed_to_counts_per_msec(value, unit, self._require_scale())
        if per_msec <= 0:
            raise ValueError("speed must be positive")
        if self.resolution is not None:
            # The drive cannot accept more than 2 MHz of step pulses.
            drive.check_step_rate(abs(per_msec) * 1000.0)
        self.motor.set_ivar(_JOG_SPEED_IVAR, per_msec)
        return per_msec

    def get_speed(self, unit: str = "cm/s") -> float:
        return units.counts_per_msec_to_speed(self.speed, unit, self._require_scale())

    # -- state and motion --------------------------------------------------

    @property
    def status(self):
        return self.motor.status

    def kill(self) -> None:
        """Disable the controller's output to this drive."""
        self.motor.kill()

    def enable(self) -> None:
        """Close the loop and hold position.

        Refuses while :meth:`check_configuration` reports a problem, so a
        channel still in PWM mode cannot be enabled into a runaway.
        """
        check = self.check_configuration()
        if not check.ok:
            raise RuntimeError(f"refusing to enable this axis.\n{check.report()}")
        self.motor.enable()

    def wait(self, timeout: float = 60.0, poll: float = 0.03) -> bool:
        """Block until the move finishes. Returns False on a fault or timeout."""
        deadline = time.time() + timeout
        started = time.time()
        while time.time() < deadline:
            status = self.motor.status
            if status.faulted:
                return False
            if status.in_position and time.time() - started > 0.3:
                return True
            time.sleep(poll)
        return False

    def move_by(self, distance: float, unit: str = "cm", wait: bool = True,
                timeout: float = 60.0) -> bool:
        """Move a relative distance. This moves the axis."""
        self.motor.jog_by(self.to_counts(distance, unit))
        return self.wait(timeout) if wait else True

    def move_to(self, position: float, unit: str = "cm", wait: bool = True,
                timeout: float = 60.0) -> bool:
        """Move to an absolute position. This moves the axis."""
        self.motor.jog_to(self.to_counts(position, unit))
        return self.wait(timeout) if wait else True

    def move_counts(self, counts: float, wait: bool = True,
                    timeout: float = 60.0) -> bool:
        """Move a relative distance in raw counts, no scale factor needed."""
        self.motor.jog_by(counts)
        return self.wait(timeout) if wait else True

    def stop(self) -> None:
        """Decelerate to a stop and hold position."""
        self.motor.stop()

    def set_zero(self) -> None:
        """Call the present position zero, without moving.

        The encoder is incremental and its counter restarts at every controller
        reset, so there is no datum until one is declared. Do this at a known
        physical reference and absolute moves become meaningful.
        """
        self.motor.home_here()
