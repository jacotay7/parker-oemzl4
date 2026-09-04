#!/usr/bin/env python3
"""Measure encoder counts per centimetre.

This number cannot be derived from any manual. The OEMZL4 has no
communications port so it cannot report its microstep resolution, and nothing
in either manual knows what mechanism the motor turns. It has to be measured
once: command a known number of counts, measure the travel, divide.

    python3 tools/calibrate.py                        # interactive, 10000 counts
    python3 tools/calibrate.py --counts -20000        # NEGATIVE moves the other way
    python3 tools/calibrate.py --counts 20000 --measured 5.2 --unit mm
                                                      # just do the arithmetic

A negative --counts moves in the opposite direction. Check which way the axis
has room before starting: if it is sitting near one end of travel, the move
must head away from that end.

Accuracy comes from a long move -- the measurement error is fixed, so doubling
the distance halves its effect -- but only use travel you can actually spare.
"""

from __future__ import annotations

import argparse
import sys
import time

from parker_oemzl4 import OEMZL4Axis, units
from turbo_pmac import PMAC


def report(counts: float, measured: float, unit: str) -> int:
    if measured == 0:
        print("measured distance was zero -- nothing to calibrate from")
        return 1
    cm = units.to_cm(abs(measured), unit)
    counts_per_cm = abs(counts) / cm
    print(f"\n  {abs(counts):,.0f} counts moved {abs(measured)} {unit} "
          f"({cm:.4f} cm)")
    print(f"\n  counts_per_cm = {counts_per_cm:,.2f}")
    print(f"  1 cm  = {counts_per_cm:,.1f} counts")
    print(f"  1 mm  = {counts_per_cm / 10:,.1f} counts")
    print(f"\nUse it like this:\n")
    print(f"    axis = OEMZL4Axis(pmac.motor(1), channel=1,")
    print(f"                      counts_per_cm={counts_per_cm:.2f})")
    print(f"    axis.set_speed(1, 'cm/s')")
    print(f"    axis.move_by(1, 'cm')")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--counts", type=float, default=10000,
                    help="counts to move; negative goes the other way (default 10000)")
    ap.add_argument("--measured", type=float,
                    help="measured travel; skips the move and just computes")
    ap.add_argument("--unit", default="mm", help="unit of --measured (default mm)")
    ap.add_argument("--motor", type=int, default=1)
    ap.add_argument("--channel", type=int, default=1)
    ap.add_argument("--no-return", action="store_true",
                    help="stay at the far end instead of returning")
    args = ap.parse_args()

    if args.measured is not None:
        return report(args.counts, args.measured, args.unit)

    with PMAC() as pmac:
        axis = OEMZL4Axis(pmac.motor(args.motor), channel=args.channel)
        check = axis.check_configuration()
        if not check.ok:
            print(check.report())
            return 1

        start = axis.position_counts
        heading = "NEGATIVE" if args.counts < 0 else "POSITIVE"
        print(f"position now: {start:,.1f} counts")
        print(f"\nAbout to move {args.counts:+,.0f} counts, in the {heading} direction,")
        print(f"ending near {start + args.counts:,.1f} counts.")
        print("\nMake sure the axis has room to travel THAT way -- this tool cannot")
        print("see the mechanism and there are no travel limits configured.")
        print("\nMark the current position, or note the reading on any scale.")
        try:
            input("Press Enter when ready, or Ctrl-C to abort... ")
        except KeyboardInterrupt:
            print("\naborted")
            return 1

        axis.enable()
        time.sleep(0.3)
        print("moving...")
        ok = axis.move_counts(args.counts, timeout=180)
        end = axis.position_counts
        moved = end - start
        status = axis.status
        axis.kill()

        if not ok:
            print(f"move did not finish cleanly: {status.summary()}")
            print(f"  flags: {', '.join(status.active_flags())}")
            print(f"  moved {moved:+,.1f} counts before stopping")
            if abs(moved) < 1:
                return 1
            print("  you can still calibrate from the distance it did travel")

        print(f"\nmoved {moved:+,.1f} counts "
              f"({start:,.1f} -> {end:,.1f})")
        try:
            raw = input(f"\nMeasure the travel and enter it in {args.unit}: ")
            measured = float(raw.strip())
        except (KeyboardInterrupt, ValueError):
            print("\nno measurement taken. Re-run with:")
            print(f"  python3 tools/calibrate.py --counts {moved:.0f} "
                  f"--measured <distance> --unit {args.unit}")
            return 1

        code = report(moved, measured, args.unit)

        if not args.no_return:
            print("\nreturning to the starting position...")
            axis.enable()
            time.sleep(0.3)
            axis.move_counts(-moved, timeout=180)
            axis.kill()
            print(f"back at {axis.position_counts:,.1f} counts")
        return code


if __name__ == "__main__":
    raise SystemExit(main())
