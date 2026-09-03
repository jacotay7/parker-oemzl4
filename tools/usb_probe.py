#!/usr/bin/env python3
"""Enumerate USB devices and dump descriptors for a Delta Tau PMAC.

macOS has no driver for Delta Tau's vendor-specific USB device, which means
nothing claims it and libusb can talk to it directly. This lists what is
attached and dumps the full descriptor of anything that looks like a PMAC, so
we can see its interfaces and endpoints before writing the transport.

    python3 tools/usb_probe.py            # list everything
    python3 tools/usb_probe.py -v         # dump every descriptor
    python3 tools/usb_probe.py 0x1234     # dump one vendor id
"""

import ctypes.util
import sys

import usb.backend.libusb1
import usb.core
import usb.util

# Hubs and the known-good Ethernet adapter -- not what we are looking for.
KNOWN_UNINTERESTING = {
    (0x2109, 0x2817),  # VIA Labs USB2.0 hub
    (0x2109, 0x0817),  # VIA Labs USB3.0 hub
    (0x0BDA, 0x8153),  # Realtek USB 10/100/1000 LAN
}

# Homebrew installs libusb outside the default search path on Apple Silicon.
def backend():
    for path in ("/opt/homebrew/lib/libusb-1.0.dylib",
                 "/usr/local/lib/libusb-1.0.dylib"):
        # pyusb calls find_library(name), so the callable must accept that arg.
        b = usb.backend.libusb1.get_backend(find_library=lambda _name, _p=path: _p)
        if b:
            return b
    return usb.backend.libusb1.get_backend(
        find_library=lambda _: ctypes.util.find_library("usb-1.0"))


def describe(dev) -> str:
    def s(attr):
        try:
            return usb.util.get_string(dev, getattr(dev, attr)) or "?"
        except Exception:
            return "?"
    return (f"{dev.idVendor:#06x}:{dev.idProduct:#06x}  "
            f"{s('iManufacturer'):<24} {s('iProduct')}")


def dump(dev) -> None:
    print(f"\n{'=' * 70}\n{describe(dev)}\n{'=' * 70}")
    print(f"  bDeviceClass   {dev.bDeviceClass}")
    print(f"  bcdUSB         {dev.bcdUSB:#06x}")
    for cfg in dev:
        print(f"  configuration {cfg.bConfigurationValue}")
        for intf in cfg:
            print(f"    interface {intf.bInterfaceNumber} alt {intf.bAlternateSetting}  "
                  f"class={intf.bInterfaceClass} sub={intf.bInterfaceSubClass} "
                  f"proto={intf.bInterfaceProtocol}")
            for ep in intf:
                direction = "IN " if usb.util.endpoint_direction(ep.bEndpointAddress) else "OUT"
                types = {0: "control", 1: "isochronous", 2: "bulk", 3: "interrupt"}
                kind = types.get(usb.util.endpoint_type(ep.bmAttributes), "?")
                print(f"      endpoint {ep.bEndpointAddress:#04x} {direction} "
                      f"{kind:<10} maxpacket={ep.wMaxPacketSize}")


def main() -> int:
    be = backend()
    if be is None:
        print("libusb not found. Install with: brew install libusb")
        return 1

    want = int(sys.argv[1], 0) if len(sys.argv) > 1 and sys.argv[1].startswith("0x") else None
    verbose = "-v" in sys.argv

    devices = list(usb.core.find(find_all=True, backend=be))
    if not devices:
        print("No USB devices visible at all -- unexpected.")
        return 1

    print(f"{len(devices)} USB device(s):\n")
    candidates = []
    for dev in devices:
        tag = ""
        if (dev.idVendor, dev.idProduct) in KNOWN_UNINTERESTING:
            tag = "  (hub / net adapter)"
        else:
            candidates.append(dev)
            tag = "  <-- candidate"
        if want and dev.idVendor != want:
            continue
        print(" ", describe(dev) + tag)

    targets = [d for d in devices if want and d.idVendor == want] or candidates
    if verbose or targets:
        for dev in (devices if verbose else targets):
            try:
                dump(dev)
            except Exception as exc:
                print(f"\n{describe(dev)}\n  cannot read descriptors: {exc}")

    if not candidates:
        print("\nNo unrecognised device. Is the Brick's USB cable plugged into this Mac?")
        return 1

    print("\nA candidate above with bulk IN and OUT endpoints is very likely the PMAC.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
