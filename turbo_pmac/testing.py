"""A fake transport, so the command layer can be tested without hardware.

It reproduces the two framing behaviours that matter and that cost real time to
discover on the live device: a reply arrives before its ``<ACK>``, and reads
return ``b""`` while nothing is ready.
"""

from __future__ import annotations

from .protocol import ACK, BEL


class FakeTransport:
    """Answers commands from a lookup table.

    :param replies: command text -> reply text. A reply may be a
        :class:`FakeError` to make the controller report a failure.
    :param ack_delay: how many empty reads to return before the ``<ACK>``,
        mimicking the device answering the terminator on a later read.
    """

    def __init__(self, replies: dict[str, object] | None = None,
                 ack_delay: int = 1, stale_ack: bool = False):
        self.replies = dict(replies or {})
        self.ack_delay = ack_delay
        self.sent: list[str] = []
        self._queue: list[bytes] = [bytes([ACK])] if stale_ack else []
        self.closed = False

    def send(self, text: str) -> None:
        self.sent.append(text)
        reply = self.replies.get(text)
        if reply is None:
            self._queue.append(bytes([ACK]))
            return

        if isinstance(reply, FakeError):
            self._queue.append(bytes([BEL]) + reply.text.encode("ascii"))
        else:
            self._queue.append(str(reply).encode("ascii") + b"\r")
        self._queue.extend([b""] * self.ack_delay)
        self._queue.append(bytes([ACK]))

    def receive(self) -> bytes:
        return self._queue.pop(0) if self._queue else b""

    def close(self) -> None:
        self.closed = True


class FakeError:
    """Marks a canned reply as an error response."""

    def __init__(self, text: str = "ERR003"):
        self.text = text
