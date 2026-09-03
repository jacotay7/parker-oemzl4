"""An OEMZL4 driven by one channel of a Turbo PMAC.

The drive is deaf and mute: it accepts step and direction pulses and reports
nothing but a single fault contact. Everything you can ask or command goes to
the controller, so this class wraps a :class:`turbo_pmac.Motor` and adds the
checks the drive's own limits imply.
"""

from __future__ import annotations

from dataclasses import dataclass

from turbo_pmac import Motor
from turbo_pmac.response import as_int

from . import drive

#: Ixx02 values that mean "this motor commands a servo IC channel's C output",
#: which is the output that can carry PFM. Servo IC 0, channels 1-4.
_C_OUTPUT_ADDRESSES = {0x78002, 0x78006, 0x7800A, 0x7800E}

#: I7mn6 settings whose C output is PFM rather than PWM.
PFM_OUTPUT_MODES = (2, 3)


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
    :param channel: the servo IC channel wired to the drive's INDEXER port,
        1-8 on a Brick Controller. Used to address the ``I7mn*`` variables.
    :param resolution: steps per revolution set on the drive's DIP switches.
        The drive cannot be asked, so it must be told.
    """

    def __init__(self, motor: Motor, channel: int = 1, resolution: int | None = None):
        if not 1 <= channel <= 8:
            raise ValueError(f"channel out of range: {channel}")
        self.motor = motor
        self.channel = channel
        self.resolution = resolution

    def __repr__(self) -> str:
        return f"<OEMZL4Axis motor #{self.motor.number} channel {self.channel}>"

    # -- servo IC addressing ----------------------------------------------

    @property
    def _servo_ic(self) -> int:
        """Servo IC index: channels 1-4 live on IC 0, channels 5-8 on IC 1."""
        return 0 if self.channel <= 4 else 1

    @property
    def _channel_in_ic(self) -> int:
        return self.channel if self.channel <= 4 else self.channel - 4

    def _i7var(self, param: int) -> str:
        """Name of an ``I7mn<param>`` variable for this channel."""
        return f"I7{self._servo_ic}{self._channel_in_ic}{param}"

    @property
    def output_mode(self) -> int:
        """I7mn6: 0/1 leave the C output as PWM, 2/3 make it PFM."""
        return as_int(self.motor.pmac.get(self._i7var(6)))

    @property
    def pulse_width_counts(self) -> int:
        """I7mn4-equivalent PFM pulse width, in PFM clock cycles."""
        return as_int(self.motor.pmac.get(f"I7{self._servo_ic}04"))

    # -- validation --------------------------------------------------------

    def check_configuration(self) -> ConfigCheck:
        """Check the controller is set up to drive a step/direction amplifier.

        Read-only. Does not move the axis and changes nothing.
        """
        problems: list[str] = []
        notes: list[str] = []

        mode = self.output_mode
        if mode not in PFM_OUTPUT_MODES:
            problems.append(
                f"{self._i7var(6)}={mode} leaves the channel's C output in PWM mode. "
                "PWM is a continuous carrier, so the drive would see an endless "
                "constant-rate step train and run continuously regardless of what "
                f"is commanded. Set it to 2 (A/B PWM) or 3 (A/B DAC) for PFM.")

        address = self.motor.output_address
        if address not in _C_OUTPUT_ADDRESSES:
            notes.append(
                f"I{self.motor.number}02=${address:X} is not a servo IC C output "
                "address; check the motor is commanding the channel wired to the drive.")

        status = self.motor.status
        if not status.activated:
            notes.append("motor is deactivated (Ixx00=0)")
        if status.faulted:
            problems.append(f"motor reports a fault: {', '.join(status.active_flags())}")

        return ConfigCheck(not problems, tuple(problems), tuple(notes))

    # -- speed limits ------------------------------------------------------

    def max_speed_rps(self) -> float:
        """Top speed in rev/s, set by the drive's 2 MHz step-rate ceiling."""
        if self.resolution is None:
            raise ValueError("resolution is unknown; read it off the drive's DIP switches")
        return drive.max_speed_rps(self.resolution)

    def check_speed_rps(self, rps: float) -> None:
        """Raise if a speed would exceed the drive's maximum step rate."""
        if self.resolution is None:
            raise ValueError("resolution is unknown; read it off the drive's DIP switches")
        drive.check_step_rate(abs(rps) * self.resolution)

    # -- state and motion --------------------------------------------------

    @property
    def status(self):
        return self.motor.status

    @property
    def position(self) -> float:
        return self.motor.position

    def kill(self) -> None:
        """Disable the controller's output to this drive."""
        self.motor.kill()

    def enable(self) -> None:
        """Close the loop and hold position.

        Refuses to run while :meth:`check_configuration` reports a problem, so
        a channel still in PWM mode cannot be enabled into a runaway.
        """
        check = self.check_configuration()
        if not check.ok:
            raise RuntimeError(f"refusing to enable this axis.\n{check.report()}")
        self.motor.enable()
