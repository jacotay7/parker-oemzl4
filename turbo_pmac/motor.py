"""One motor on a Turbo PMAC."""

from __future__ import annotations

from . import response
from .status import MotorStatus


class Motor:
    """Addresses a single motor, e.g. ``#1``.

    Motion methods are named for what they do to the machine and none of them
    is implicit: nothing here moves an axis unless you call something that says
    it moves an axis.
    """

    def __init__(self, pmac, number: int):
        if not 1 <= number <= 32:
            raise ValueError(f"motor number out of range: {number}")
        self.pmac = pmac
        self.number = number

    def __repr__(self) -> str:
        return f"<Motor #{self.number}>"

    @property
    def prefix(self) -> str:
        return f"#{self.number}"

    def command(self, text: str) -> str:
        """Send a command addressed to this motor."""
        return self.pmac.command(f"{self.prefix}{text}")

    # -- variables ---------------------------------------------------------

    def ivar(self, offset: int) -> str:
        """Read this motor's ``Ixx`` variable, e.g. ``ivar(30)`` -> ``I130``."""
        return self.pmac.get(f"I{self.number}{offset:02d}")

    def set_ivar(self, offset: int, value) -> None:
        self.pmac.set(f"I{self.number}{offset:02d}", value)

    # -- state -------------------------------------------------------------

    @property
    def status(self) -> MotorStatus:
        return MotorStatus.parse(self.command("?"))

    @property
    def position(self) -> float:
        return response.as_float(self.command("P"))

    @property
    def velocity(self) -> float:
        return response.as_float(self.command("V"))

    @property
    def following_error(self) -> float:
        return response.as_float(self.command("F"))

    @property
    def activated(self) -> bool:
        """Ixx00: whether the controller runs calculations for this motor."""
        return response.as_bool(self.ivar(0))

    # -- output configuration ---------------------------------------------

    @property
    def output_address(self) -> int:
        """Ixx02, the register this motor commands."""
        return response.as_int(self.ivar(2))

    # -- motion ------------------------------------------------------------

    def kill(self) -> None:
        """Disable this motor's outputs: open loop, zero output, amp disabled."""
        self.command("K")

    def enable(self) -> None:
        """Close the servo loop and hold present position (``J/``)."""
        self.command("J/")

    def stop(self) -> None:
        """Decelerate to a stop and hold position."""
        self.command("J/")

    def jog_positive(self) -> None:
        """Jog indefinitely in the positive direction. This moves the axis."""
        self.command("J+")

    def jog_negative(self) -> None:
        """Jog indefinitely in the negative direction. This moves the axis."""
        self.command("J-")

    def jog_to(self, position: float) -> None:
        """Jog to an absolute position. This moves the axis."""
        self.command(f"J={position}")

    def jog_by(self, distance: float) -> None:
        """Jog a relative distance. This moves the axis."""
        self.command(f"J^{distance}")

    def home(self) -> None:
        """Start a homing search. This moves the axis."""
        self.command("HM")
