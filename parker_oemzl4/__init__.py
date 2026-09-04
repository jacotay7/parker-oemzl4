"""Parker Hannifin / Compumotor **OEMZL4** step motor drive.

The OEMZL4 is an amplifier, not a controller. It has no communications port of
any kind, so this package holds reference data from its manuals plus a thin
axis wrapper that adds the drive's limits to a controller motor.

The controller doing the talking lives in its own package, :mod:`turbo_pmac`,
which knows nothing about this drive and can be reused on its own.

    >>> from turbo_pmac import PMAC                       # doctest: +SKIP
    >>> from parker_oemzl4 import OEMZL4Axis
    >>> with PMAC() as pmac:
    ...     axis = OEMZL4Axis(pmac.motor(1), channel=1, resolution=25000)
    ...     print(axis.check_configuration().report())
"""

from . import drive, machine, units
from .axis import ConfigCheck, OEMZL4Axis, c_output_address
from .drive import (
    CURRENTS, FAULT_CAUSES, MAX_STEP_RATE_HZ, MIN_PULSE_NS, PINOUT,
    PINOUT_CW_CCW, RESOLUTIONS, SignalSpec, current_amps, max_speed_rps,
    steps_per_rev,
)

__version__ = "0.1.0"

__all__ = [
    "OEMZL4Axis",
    "ConfigCheck",
    "drive",
    "units",
    "machine",
    "c_output_address",
    "PINOUT",
    "PINOUT_CW_CCW",
    "RESOLUTIONS",
    "CURRENTS",
    "FAULT_CAUSES",
    "MAX_STEP_RATE_HZ",
    "MIN_PULSE_NS",
    "SignalSpec",
    "steps_per_rev",
    "current_amps",
    "max_speed_rps",
]
