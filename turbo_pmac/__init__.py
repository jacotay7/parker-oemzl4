"""Control library for Delta Tau / Omron **Turbo PMAC** motion controllers.

Verified against a Brick Motion Controller ``BC8-C0-DD2-130-00000`` running
firmware 1.947, over USB on macOS with libusb and no Delta Tau driver.

Nothing here is specific to any particular machine, so it can be reused with
any Turbo PMAC. Drive- and rig-specific knowledge belongs in its own package;
see ``parker_oemzl4`` in this repository for an example.

    >>> from turbo_pmac import PMAC              # doctest: +SKIP
    >>> with PMAC() as pmac:
    ...     print(pmac.version)
    ...     print(pmac.motor(1).status.summary())
"""

from .controller import PMAC
from .errors import (
    CommandError, DeviceNotFound, PMACError, TransportError,
)
from .motor import Motor
from .status import MotorStatus
from .testing import FakeError, FakeTransport
from .transport import EthernetTransport, Transport, USBTransport

__version__ = "0.1.0"

__all__ = [
    "PMAC",
    "Motor",
    "MotorStatus",
    "Transport",
    "USBTransport",
    "EthernetTransport",
    "FakeTransport",
    "FakeError",
    "PMACError",
    "TransportError",
    "DeviceNotFound",
    "CommandError",
]
