#!/usr/bin/env python3
"""Hold a steady PFM output so the drive's front panel can be watched.

The OEMZL4's STEP LED goes green when the drive receives a step pulse. That
makes it the fastest way to tell whether pulses are actually arriving, which no
amount of reading the controller can settle.

    python3 tools/pulse_test.py            # 15 s at 1% output
    python3 tools/pulse_test.py 3 30       # 30 s at 3% output

Watch, in order:
  POWER        green      drive is powered
  STEP         green      pulses ARE arriving  -> problem is downstream
               dark       no pulses            -> problem is the cable or the
                                                  controller output stage
  MOTOR FAULT  red        short circuit, motor disconnected, or interlock open
  OVER TEMP    red        over temperature
"""

import sys
import time

from turbo_pmac import PMAC


def main() -> int:
    output = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0

    with PMAC() as pmac:
        motor = pmac.motor(1)
        motor.enable()
        time.sleep(0.3)
        if motor.status.faulted:
            print("motor faulted before we started:",
                  ", ".join(motor.status.active_flags()))
            motor.kill()
            return 1

        start = motor.position
        print(f"commanding {output}% open-loop output for {seconds:.0f} s.")
        print("WATCH THE DRIVE'S STEP LED NOW.\n")
        pmac.command(f"#1O{output}")

        try:
            t0 = time.time()
            while time.time() - t0 < seconds:
                pos = motor.position
                print(f"  t={time.time()-t0:5.1f}s  position {pos:>12}"
                      f"   moved {pos-start:+.1f}", end="\r", flush=True)
                time.sleep(0.5)
        finally:
            motor.kill()

        end = motor.position
        print(f"\n\nmoved {end-start:+.1f} counts in {seconds:.0f} s")
        print("motor left killed:", motor.status.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
