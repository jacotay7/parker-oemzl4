#!/usr/bin/env python3
"""Move the stage in physical units.

    python3 examples/basic_move.py

Read the axis, move a millimetre out and back, and report what happened. Safe
to run: the moves are small and it returns to where it started.
"""

import time

from parker_oemzl4.machine import connect, describe


def main() -> None:
    print(describe(), "\n")

    with connect() as axis:
        check = axis.check_configuration()
        if not check.ok:
            print(check.report())
            return

        print(f"start      {axis.position('mm'):9.3f} mm")
        print(f"state      {axis.status.summary()}")

        axis.set_speed(2, "mm/s")
        print(f"speed      {axis.get_speed('mm/s'):9.3f} mm/s\n")

        axis.enable()
        time.sleep(0.3)

        for distance in (+1.0, -1.0):
            started = time.time()
            axis.move_by(distance, "mm")
            print(f"move {distance:+.1f} mm -> {axis.position('mm'):9.3f} mm"
                  f"   in {time.time()-started:.2f}s")

        print(f"\nend        {axis.position('mm'):9.3f} mm")
        # connect() kills the axis on the way out, however this block ends.


if __name__ == "__main__":
    main()
