#!/usr/bin/env python3
"""Minimal USB transport for a Delta Tau Turbo PMAC, plus a read-only survey.

Verified against a Brick Motion Controller BC8-C0-DD2-130-00000 running Turbo
PMAC firmware 1.947, over USB on macOS with libusb -- no Delta Tau driver.

Protocol, per the ACC-54E manual: the ETHERNETCMD struct is exactly a USB
control setup packet, so each exchange is a pair of control transfers:
    SENDLINE (0xB0)  host -> device, carrying the command text
    GETLINE  (0xB1)  device -> host, returning the reply

Two behaviours the manual does not spell out, both found by experiment:
  * GETLINE returns a NUL byte when nothing is ready yet. It neither blocks
    nor returns a zero-length transfer, so the caller must poll for real data.
  * The <ACK> terminating a reply usually arrives on a later read than the
    reply text. A command must keep reading until it sees ACK or its deadline
    passes; stopping early leaves the ACK queued, where it is mistaken for the
    next command's reply and desynchronises every command after it.

    python3 tools/pmac.py                 # read-only survey
    python3 tools/pmac.py "I7010" "#1P"   # ad-hoc queries
"""

import sys
import time

import usb.backend.libusb1
import usb.core
import usb.util

VID, PID = 0x0AA2, 0x0007  # Delta Tau Data Systems / ACC54E USB2

VR_DOWNLOAD, VR_UPLOAD = 0x40, 0xC0
VR_PMAC_SENDLINE, VR_PMAC_GETLINE = 0xB0, 0xB1

ACK, BEL, STX = 0x06, 0x07, 0x02


class PMACError(RuntimeError):
    """The controller answered with an error string."""


class PMAC:
    def __init__(self, timeout_ms: int = 300, reply_timeout_s: float = 1.5):
        self.timeout = timeout_ms
        self.reply_timeout = reply_timeout_s
        self.dev = usb.core.find(idVendor=VID, idProduct=PID, backend=self._backend())
        if self.dev is None:
            raise RuntimeError(f"No Delta Tau {VID:#06x}:{PID:#06x} on USB")
        try:
            self.dev.set_configuration()
        except usb.core.USBError as exc:
            if "busy" not in str(exc).lower():
                raise
        usb.util.claim_interface(self.dev, 0)

    @staticmethod
    def _backend():
        for path in ("/opt/homebrew/lib/libusb-1.0.dylib",
                     "/usr/local/lib/libusb-1.0.dylib"):
            b = usb.backend.libusb1.get_backend(find_library=lambda _n, _p=path: _p)
            if b:
                return b
        return None

    def close(self):
        usb.util.dispose_resources(self.dev)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # -- raw transfers -----------------------------------------------------

    def _getline(self) -> bytes:
        """One GETLINE. NUL padding is stripped, so b'' means 'nothing ready'."""
        try:
            raw = bytes(self.dev.ctrl_transfer(VR_UPLOAD, VR_PMAC_GETLINE,
                                               0, 0, 1400, timeout=self.timeout))
        except usb.core.USBError:
            return b""
        return raw.replace(b"\x00", b"")

    def _sendline(self, text: str) -> None:
        self.dev.ctrl_transfer(VR_DOWNLOAD, VR_PMAC_SENDLINE, 0, 0,
                               (text + "\r").encode("ascii"), timeout=1000)

    def drain(self, seconds: float = 0.3) -> bytes:
        """Discard anything left queued from an earlier command.

        Poll for the whole window rather than stopping at the first empty
        read: a trailing <ACK> often is not ready the instant we look, and one
        left behind will terminate the next command's read before its reply
        arrives.
        """
        leftover, deadline = b"", time.time() + seconds
        while time.time() < deadline:
            chunk = self._getline()
            if chunk:
                leftover += chunk
            else:
                time.sleep(0.004)
        return leftover

    # -- command layer -----------------------------------------------------

    def command(self, text: str) -> str:
        """Send one command and return its reply, stripped of framing.

        Deliberately does NOT drain first. Issuing GETLINE while no command is
        pending wedges this device -- every subsequent reply comes back empty
        until it is power-cycled. Sync is kept instead by ignoring a bare
        leftover <ACK> in the read loop below.
        """
        self._sendline(text)

        out, error, saw_ack = [], False, False
        deadline = time.time() + self.reply_timeout
        while time.time() < deadline and not saw_ack:
            chunk = self._getline()
            if not chunk:
                time.sleep(0.004)
                continue
            if chunk[0] in (BEL, STX):
                error = True
                chunk = chunk[1:]
            body = chunk.replace(bytes([ACK]), b"")
            if ACK in chunk:
                # A bare ACK before any data is a leftover from an earlier
                # command that drain() did not catch. Ignore it and keep
                # waiting for this command's own reply.
                if not body and not out:
                    continue
                saw_ack = True
            if body:
                out.append(body.decode("ascii", "replace"))

        reply = "".join(out).replace("\r", "\n").strip()
        if error:
            raise PMACError(f"{text}: {reply}")
        return reply


SURVEY = [
    ("Firmware version", "VERSION"),
    ("Card type", "TYPE"),
    ("Global status", "???"),
    ("Motor 1 status", "#1?"),
    ("Motor 1 commanded position", "#1P"),
    ("Motor 1 velocity", "#1V"),
    ("Motor 1 following error", "#1F"),
    ("PLC enable mask (I5)", "I5"),
    ("Motor 1 activated (I100)", "I100"),
    ("Motor 1 commutation enable (I101)", "I101"),
    ("Motor 1 output address (I102)", "I102"),
    ("Motor 1 pos feedback addr (I103)", "I103"),
    ("Motor 1 vel feedback addr (I104)", "I104"),
    ("Motor 1 fatal following err (I111)", "I111"),
    ("Motor 1 proportional gain (I130)", "I130"),
    ("Motor 1 max output (I169)", "I169"),
    ("Ch1 encoder decode (I7010)", "I7010"),
    ("Ch1 output mode (I7016)", "I7016"),
    ("Ch1 PFM dir invert (I7018)", "I7018"),
    ("Servo IC0 PFM clock (I7002)", "I7002"),
    ("Servo IC0 pulse width (I7004)", "I7004"),
]


def main() -> int:
    if len(sys.argv) > 1:
        with PMAC() as pmac:
            for cmd in sys.argv[1:]:
                print(f"{cmd:<10} {pmac.command(cmd)!r}")
        return 0

    with PMAC() as pmac:
        print("Delta Tau Turbo PMAC -- read-only survey\n")
        for label, cmd in SURVEY:
            try:
                print(f"  {label:<36} {cmd:<8} {pmac.command(cmd)!r}")
            except PMACError as exc:
                print(f"  {label:<36} {cmd:<8} ERROR {exc}")
            except usb.core.USBError as exc:
                print(f"  {label:<36} {cmd:<8} USB {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
