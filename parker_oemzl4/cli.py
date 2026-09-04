"""Command line for the OEMZL4 stage.

    oemzl4 status                 where it is, and whether it is healthy
    oemzl4 move 1cm               relative move
    oemzl4 move -5mm --speed 2mm/s
    oemzl4 moveto 2cm             absolute, relative to the zero reference
    oemzl4 zero                   call the present position zero, without moving
    oemzl4 stop                   kill the axis output now
    oemzl4 check                  verify the controller configuration

Distances accept a unit attached or separate: ``1cm``, ``-5 mm``, ``2.5in``.
Speeds look like ``1cm/s`` or ``30mm/min``.
"""

from __future__ import annotations

import argparse
import re
import sys

from turbo_pmac.errors import PMACError

from . import units
from .machine import COUNTS_PER_CM, connect, describe

_QUANTITY = re.compile(r"^\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?\d+)?)\s*(.*?)\s*$")

# A negative quantity with a unit -- "-5mm", "-1.5cm/s" -- starts with a dash,
# so argparse reads it as an option flag and refuses it. argparse only exempts
# bare negative numbers. Nothing matching this can be a real option, so pad it
# with a leading space: argparse then sees a positional, and _QUANTITY skips
# the space when parsing.
_NEGATIVE_QUANTITY = re.compile(r"^-[0-9]*\.?[0-9]+(?:[eE][-+]?\d+)?\s*[a-zA-Z]+(?:/[a-zA-Z]+)?$")


def allow_negative_quantities(argv: list[str]) -> list[str]:
    """Let ``move -5mm`` through argparse without needing a ``--`` separator."""
    return [f" {tok}" if _NEGATIVE_QUANTITY.match(tok) else tok for tok in argv]


def parse_quantity(text: str, default_unit: str) -> tuple[float, str]:
    """Split ``"1cm"`` or ``"1 cm"`` into a value and a unit."""
    match = _QUANTITY.match(text)
    if not match:
        raise ValueError(f"cannot read a number from {text!r}")
    value, unit = match.group(1), match.group(2)
    return float(value), (unit or default_unit)


def _status(axis, args) -> int:
    status = axis.status
    print(f"position  {axis.position('mm'):10.3f} mm"
          f"   ({axis.position_counts:,.1f} counts)")
    print(f"speed     {axis.get_speed('mm/s'):10.3f} mm/s")
    print(f"state     {status.summary()}")
    if status.active_flags():
        print(f"flags     {', '.join(status.active_flags())}")
    print(f"scale     {describe()}")
    return 0


def _check(axis, args) -> int:
    check = axis.check_configuration()
    print(check.report())
    return 0 if check.ok else 1


def _pos(axis, args) -> int:
    print(f"{axis.position(args.unit):.4f} {args.unit}")
    return 0


def _move(axis, args) -> int:
    distance, unit = parse_quantity(args.distance, args.unit)
    if args.speed:
        value, speed_unit = parse_quantity(args.speed, "cm/s")
        axis.set_speed(value, speed_unit)

    absolute = args.action == "moveto"
    target = distance if absolute else axis.position(unit) + distance
    print(f"{'moving to' if absolute else 'moving'} {distance:+g} {unit}"
          f"   ({axis.position(unit):.4f} -> {target:.4f} {unit})"
          f"   at {axis.get_speed('mm/s'):.3f} mm/s")

    axis.enable()
    done = (axis.move_to(distance, unit) if absolute
            else axis.move_by(distance, unit))
    status = axis.status
    print(f"arrived   {axis.position('mm'):10.3f} mm   ({axis.position_counts:,.1f} counts)")
    if not done:
        print(f"WARNING: move did not complete cleanly -- {status.summary()}")
        if status.active_flags():
            print(f"  flags: {', '.join(status.active_flags())}")
        return 1
    return 0


def _zero(axis, args) -> int:
    before = axis.position_counts
    axis.set_zero()
    print(f"zero set here (was {before:,.1f} counts)")
    print(f"position now {axis.position('mm'):.3f} mm")
    return 0


def _speed(axis, args) -> int:
    value, unit = parse_quantity(args.value, "cm/s")
    axis.set_speed(value, unit)
    print(f"speed now {axis.get_speed('mm/s'):.3f} mm/s "
          f"({axis.get_speed('cm/s'):.3f} cm/s)")
    return 0


def _stop(axis, args) -> int:
    axis.kill()
    print("axis killed:", axis.status.summary())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oemzl4", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--unit", default="mm",
                        help="default unit when one is not given (default mm)")
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("status", help="position, speed and state")
    sub.add_parser("check", help="verify the controller configuration")
    sub.add_parser("pos", help="print the position only")
    sub.add_parser("zero", help="call the present position zero, without moving")
    sub.add_parser("stop", help="kill the axis output now")

    for name, helptext in [("move", "relative move, e.g. 1cm"),
                           ("moveto", "absolute move, e.g. 2cm")]:
        p = sub.add_parser(name, help=helptext)
        p.add_argument("distance")
        p.add_argument("--speed", help="set the speed first, e.g. 2mm/s")

    p = sub.add_parser("speed", help="set the speed, e.g. 1cm/s")
    p.add_argument("value")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = allow_negative_quantities(list(sys.argv[1:] if argv is None else argv))
    args = build_parser().parse_args(argv)
    actions = {"status": _status, "check": _check, "pos": _pos, "move": _move,
               "moveto": _move, "zero": _zero, "speed": _speed, "stop": _stop}
    try:
        with connect() as axis:
            return actions[args.action](axis, args)
    except (PMACError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrupted -- axis killed", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
