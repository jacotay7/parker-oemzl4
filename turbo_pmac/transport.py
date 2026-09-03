"""Transports carrying the PMAC protocol.

:class:`USBTransport` is the one verified against hardware. macOS has no driver
for Delta Tau's vendor-specific USB device, so nothing claims it and libusb can
talk to it directly -- their ``PMACUSB.SYS`` is only needed by Delta Tau's own
Windows software.
"""

from __future__ import annotations

import socket
import time
from typing import Protocol

from .errors import DeviceNotFound, TransportError
from .protocol import (
    ACK, DEFAULT_IP, PMAC_PORT, USB_PRODUCT_ID, USB_VENDOR_ID,
    VR_DOWNLOAD, VR_PMAC_GETLINE, VR_PMAC_GETRESPONSE, VR_PMAC_SENDLINE,
    VR_UPLOAD, pack,
)

_LIBUSB_PATHS = (
    "/opt/homebrew/lib/libusb-1.0.dylib",  # Homebrew on Apple Silicon
    "/usr/local/lib/libusb-1.0.dylib",  # Homebrew on Intel
)


class Transport(Protocol):
    """What :class:`~turbo_pmac.controller.PMAC` needs from a link."""

    def send(self, text: str) -> None: ...

    def receive(self) -> bytes: ...

    def close(self) -> None: ...


class USBTransport:
    """Control-transfer transport over libusb.

    Three device behaviours are handled here because no manual documents them,
    and each one silently corrupts communication if ignored:

    1. :meth:`receive` returns ``b""`` when the device has nothing ready. The
       device answers a NUL byte rather than blocking or returning a
       zero-length transfer, so callers must poll.
    2. The ``<ACK>`` terminating a reply usually arrives on a later read than
       the reply text. :class:`~turbo_pmac.controller.PMAC` keeps reading until
       it sees one.
    3. Reading while no command is pending wedges the device -- every later
       reply comes back empty until it is power-cycled. There is deliberately
       no drain-before-send here for that reason.
    """

    def __init__(self, vendor_id: int = USB_VENDOR_ID, product_id: int = USB_PRODUCT_ID,
                 timeout_ms: int = 300, write_timeout_ms: int = 1000):
        try:
            import usb.backend.libusb1
            import usb.core
            import usb.util
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise TransportError(
                "pyusb is required for the USB transport: pip install pyusb"
            ) from exc

        self._usb = usb
        self.timeout = timeout_ms
        self.write_timeout = write_timeout_ms

        backend = self._find_backend(usb)
        device = usb.core.find(idVendor=vendor_id, idProduct=product_id, backend=backend)
        if device is None:
            raise DeviceNotFound(
                f"no Delta Tau device {vendor_id:#06x}:{product_id:#06x} on USB"
            )
        try:
            device.set_configuration()
        except usb.core.USBError as exc:
            if "busy" not in str(exc).lower():
                raise TransportError(f"cannot configure device: {exc}") from exc
        try:
            usb.util.claim_interface(device, 0)
        except Exception as exc:  # pragma: no cover - platform dependent
            raise TransportError(f"cannot claim interface 0: {exc}") from exc
        self.device = device

    @staticmethod
    def _find_backend(usb):
        import ctypes.util
        for path in _LIBUSB_PATHS:
            # pyusb calls find_library(name), so the callable must take it.
            backend = usb.backend.libusb1.get_backend(
                find_library=lambda _name, _p=path: _p)
            if backend is not None:
                return backend
        backend = usb.backend.libusb1.get_backend(
            find_library=lambda _n: ctypes.util.find_library("usb-1.0"))
        if backend is None:
            raise TransportError(
                "libusb not found. Install it with: brew install libusb")
        return backend

    def send(self, text: str) -> None:
        try:
            self.device.ctrl_transfer(VR_DOWNLOAD, VR_PMAC_SENDLINE, 0, 0,
                                      (text + "\r").encode("ascii"),
                                      timeout=self.write_timeout)
        except Exception as exc:
            raise TransportError(f"send failed: {exc}") from exc

    def receive(self) -> bytes:
        """One read. ``b""`` means nothing was ready."""
        try:
            raw = bytes(self.device.ctrl_transfer(VR_UPLOAD, VR_PMAC_GETLINE,
                                                  0, 0, 1024, timeout=self.timeout))
        except Exception:
            return b""
        return raw.replace(b"\x00", b"")

    def close(self) -> None:
        try:
            self._usb.util.dispose_resources(self.device)
        except Exception:  # pragma: no cover
            pass


class EthernetTransport:
    """Transport over TCP to :data:`~turbo_pmac.protocol.PMAC_PORT`.

    Untested: the Brick this library was developed against answers nothing on
    Ethernet, so this path is written from the ACC-54E manual alone. Prefer
    :class:`USBTransport` unless you know the controller's address.
    """

    def __init__(self, host: str = DEFAULT_IP, port: int = PMAC_PORT,
                 timeout_s: float = 3.0):
        try:
            self.sock = socket.create_connection((host, port), timeout=timeout_s)
        except OSError as exc:
            raise DeviceNotFound(f"no controller at {host}:{port}: {exc}") from exc
        self.host = host
        self._pending = b""

    def send(self, text: str) -> None:
        data = text.encode("ascii")
        try:
            self.sock.sendall(pack(VR_UPLOAD, VR_PMAC_GETRESPONSE, data=data))
        except OSError as exc:
            raise TransportError(f"send failed: {exc}") from exc

    def receive(self) -> bytes:
        try:
            return self.sock.recv(1500)
        except socket.timeout:
            return b""
        except OSError as exc:
            raise TransportError(f"receive failed: {exc}") from exc

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:  # pragma: no cover
            pass
