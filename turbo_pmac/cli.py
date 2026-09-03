"""Command line for a Turbo PMAC.

    python -m turbo_pmac probe
    python -m turbo_pmac status 1
    python -m turbo_pmac send "#1P" I130
    python -m turbo_pmac estop
"""

from __future__ import annotations

import argparse
import sys

from .controller import PMAC
from .errors import PMACError
from .status import MotorStatus

SURVEY = [
    ("Firmware version", "VERSION"),
    ("Card type", "TYPE"),
    ("Global status", "???"),
    ("PLC enable mask (I5)", "I5"),
]

MOTOR_SURVEY = [
    ("activated (Ixx00)", 0),
    ("commutation enable (Ixx01)", 1),
    ("output address (Ixx02)", 2),
    ("position feedback addr (Ixx03)", 3),
    ("velocity feedback addr (Ixx04)", 4),
    ("fatal following error (Ixx11)", 11),
    ("proportional gain (Ixx30)", 30),
    ("max output (Ixx69)", 69),
]


def _probe(pmac: PMAC, args) -> int:
    for label, cmd in SURVEY:
        print(f"  {label:<28} {pmac.command(cmd)}")
    for number in args.motors:
        motor = pmac.motor(number)
        status = motor.status
        print(f"\nMotor {number}: {status.summary()}")
        print(f"  position {motor.position}   velocity {motor.velocity}"
              f"   following error {motor.following_error}")
        print(f"  flags: {', '.join(status.active_flags()) or 'none'}")
        for label, offset in MOTOR_SURVEY:
            print(f"    {label:<32} {motor.ivar(offset)}")
    return 0


def _status(pmac: PMAC, args) -> int:
    for number in args.motors:
        status = pmac.motor(number).status
        print(f"Motor {number}: {status.summary()}   [{status.raw}]")
        for flag in status.active_flags():
            print(f"  {flag}")
    return 0


def _send(pmac: PMAC, args) -> int:
    for command in args.commands:
        try:
            print(f"{command:<12} {pmac.command(command)!r}")
        except PMACError as exc:
            print(f"{command:<12} ERROR {exc}", file=sys.stderr)
    return 0


def _estop(pmac: PMAC, args) -> int:
    pmac.emergency_stop()
    print("PLCs disabled and all motors killed.")
    for number in args.motors:
        print(f"  motor {number}: {pmac.motor(number).status.summary()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="turbo_pmac", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--motors", type=int, nargs="*", default=[1],
                        help="motor numbers to report (default: 1)")
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("probe", help="identify the controller and survey motors")
    sub.add_parser("status", help="decode motor status words")
    p_send = sub.add_parser("send", help="send raw commands")
    p_send.add_argument("commands", nargs="+")
    sub.add_parser("estop", help="disable all PLCs, then kill all motors")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    actions = {"probe": _probe, "status": _status, "send": _send, "estop": _estop}
    try:
        with PMAC() as pmac:
            return actions[args.action](pmac, args)
    except PMACError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
