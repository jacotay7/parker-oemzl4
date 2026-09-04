"""Converting between encoder counts and physical units.

The scale factor cannot be derived from any manual. The OEMZL4 has no
communications port, so it cannot report its microstep resolution, and neither
manual knows the mechanism the motor is coupled to. It has to be measured once,
by commanding a known number of counts and measuring the travel --
``tools/calibrate.py`` does exactly that.
"""

from __future__ import annotations

#: Length units, expressed as centimetres per unit.
LENGTH_UNITS = {
    "cm": 1.0,
    "mm": 0.1,
    "m": 100.0,
    "um": 1e-4,
    "micron": 1e-4,
    "in": 2.54,
    "inch": 2.54,
    "mil": 2.54e-3,
}


def _split_rate(unit: str) -> tuple[str, float]:
    """Split a rate like ``"mm/s"`` into its length unit and seconds factor."""
    text = unit.strip().lower().replace(" ", "")
    for sep in ("/",):
        if sep in text:
            length, _, per = text.partition(sep)
            break
    else:
        raise ValueError(f"not a rate unit: {unit!r} (expected something like 'cm/s')")

    seconds = {"s": 1.0, "sec": 1.0, "second": 1.0,
               "min": 60.0, "minute": 60.0}.get(per)
    if seconds is None:
        raise ValueError(f"unknown time unit in {unit!r}")
    return length, seconds


def to_cm(value: float, unit: str = "cm") -> float:
    """Convert a length into centimetres."""
    key = unit.strip().lower()
    if key not in LENGTH_UNITS:
        raise ValueError(f"unknown length unit {unit!r}; "
                         f"known: {', '.join(sorted(LENGTH_UNITS))}")
    return value * LENGTH_UNITS[key]


def from_cm(value_cm: float, unit: str = "cm") -> float:
    """Convert centimetres into another length unit."""
    key = unit.strip().lower()
    if key not in LENGTH_UNITS:
        raise ValueError(f"unknown length unit {unit!r}")
    return value_cm / LENGTH_UNITS[key]


def length_to_counts(value: float, unit: str, counts_per_cm: float) -> float:
    """Convert a length into encoder counts."""
    return to_cm(value, unit) * counts_per_cm


def counts_to_length(counts: float, unit: str, counts_per_cm: float) -> float:
    """Convert encoder counts into a length."""
    if counts_per_cm == 0:
        raise ValueError("counts_per_cm must be non-zero")
    return from_cm(counts / counts_per_cm, unit)


def speed_to_counts_per_msec(value: float, unit: str, counts_per_cm: float) -> float:
    """Convert a speed into the units of Ixx22, counts per millisecond."""
    length_unit, seconds = _split_rate(unit)
    counts_per_second = to_cm(value, length_unit) * counts_per_cm / seconds
    return counts_per_second / 1000.0


def counts_per_msec_to_speed(counts_per_msec: float, unit: str,
                             counts_per_cm: float) -> float:
    """Convert Ixx22's counts per millisecond into a speed."""
    if counts_per_cm == 0:
        raise ValueError("counts_per_cm must be non-zero")
    length_unit, seconds = _split_rate(unit)
    cm_per_second = counts_per_msec * 1000.0 / counts_per_cm
    return from_cm(cm_per_second, length_unit) * seconds
