"""The controller object: framing, command dispatch, and global operations."""

from __future__ import annotations

import time

from . import response
from .errors import TransportError
from .motor import Motor
from .protocol import ACK, BEL, CTRL_DISABLE_PLCS, CTRL_KILL_ALL, STX
from .transport import Transport, USBTransport


class PMAC:
    """A Turbo PMAC controller.

    >>> with PMAC() as pmac:              # doctest: +SKIP
    ...     pmac.version
    ...     pmac.motor(1).status.summary()
    """

    def __init__(self, transport: Transport | None = None,
                 reply_timeout_s: float = 1.5):
        self.transport = transport if transport is not None else USBTransport()
        self.reply_timeout = reply_timeout_s

    # -- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        self.transport.close()

    def __enter__(self) -> "PMAC":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # -- command layer -----------------------------------------------------

    def command(self, text: str) -> str:
        """Send one command and return its reply.

        Raises :class:`~turbo_pmac.errors.CommandError` if the controller
        flagged the reply as an error.
        """
        self.transport.send(text)

        chunks: list[str] = []
        error = False
        deadline = time.time() + self.reply_timeout

        while time.time() < deadline:
            raw = self.transport.receive()
            if not raw:
                time.sleep(0.004)
                continue

            if raw[0] in (BEL, STX):
                error = True
                raw = raw[1:]
            body = raw.replace(bytes([ACK]), b"")

            if ACK in raw:
                # A bare ACK arriving before any text is left over from an
                # earlier command. Swallowing it here keeps this reply -- and
                # every later one -- aligned with its command.
                if not body and not chunks:
                    continue
                if body:
                    chunks.append(body.decode("ascii", "replace"))
                break
            if body:
                chunks.append(body.decode("ascii", "replace"))

        text_out = "".join(chunks).replace("\r", "\n").strip()
        return response.check(text, text_out, error)

    def send(self, text: str) -> None:
        """Send a command whose reply is not wanted."""
        self.command(text)

    # -- variables ---------------------------------------------------------

    def get(self, name: str) -> str:
        """Read one variable, e.g. ``pmac.get("I130")``."""
        return self.command(name)

    def get_int(self, name: str) -> int:
        return response.as_int(self.get(name))

    def get_float(self, name: str) -> float:
        return response.as_float(self.get(name))

    def set(self, name: str, value) -> None:
        """Write one variable. Not persisted until :meth:`save` is called."""
        self.command(f"{name}={value}")

    def save(self) -> None:
        """Persist I-variables to flash so they survive a power cycle.

        Deliberately explicit: without this, every change made through
        :meth:`set` is lost on reset, which is often the safer state while a
        configuration is still being worked out.
        """
        self.command("SAVE")

    # -- identity ----------------------------------------------------------

    @property
    def version(self) -> str:
        """Firmware version, e.g. ``"1.947"``."""
        return self.command("VERSION")

    @property
    def card_type(self) -> str:
        """Card type, e.g. ``"TURBO2, X4"``."""
        return self.command("TYPE")

    @property
    def global_status(self) -> str:
        """Raw global status words from ``???``."""
        return self.command("???")

    # -- motors ------------------------------------------------------------

    def motor(self, number: int) -> Motor:
        """Address one motor, 1-8 on a Brick Controller."""
        return Motor(self, number)

    # -- global safety -----------------------------------------------------

    def disable_plcs(self) -> None:
        """<CTRL-D>: stop every PLC program."""
        self.transport.send(CTRL_DISABLE_PLCS)

    def kill_all(self) -> None:
        """<CTRL-K>: kill every motor -- open the loop, zero the output, drop
        amplifier enable.

        Note the ordering that matters in an emergency: call
        :meth:`disable_plcs` first, or a running PLC can re-command motion
        immediately afterwards.

        This is not ``<CTRL-A>``. That command aborts programs but also
        "brings any disabled or open loop motors to an enabled zero-velocity
        closed-loop state" -- it *enables* motors, so it is the wrong choice
        for stopping a runaway.
        """
        self.transport.send(CTRL_KILL_ALL)

    def emergency_stop(self) -> None:
        """Stop everything: PLCs first, then all motor outputs."""
        self.disable_plcs()
        self.kill_all()
