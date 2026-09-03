"""Turn raw controller replies into Python values."""

from __future__ import annotations

import re

from .errors import CommandError
from .protocol import ACK, BEL, CR, STX

_ERR = re.compile(r"ERR(\d+)", re.I)


def clean(raw: bytes) -> tuple[str, bool]:
    """Strip framing from a raw reply.

    Returns the text and whether the controller flagged it as an error. NUL
    padding is dropped: the USB transport returns NUL when nothing is ready,
    so it never carries meaning.
    """
    data = raw.replace(b"\x00", b"")
    error = bool(data) and data[0] in (BEL, STX)
    if error:
        data = data[1:]
    data = data.replace(bytes([ACK]), b"").replace(bytes([BEL]), b"")
    text = data.decode("ascii", "replace").replace(chr(CR), "\n")
    return text.strip(), error


def check(command: str, text: str, error: bool) -> str:
    """Raise :class:`CommandError` if the controller reported a failure."""
    if not error:
        return text
    match = _ERR.search(text)
    raise CommandError(command, text, int(match.group(1)) if match else None)


def as_int(text: str) -> int:
    """Parse an integer reply, accepting Delta Tau's ``$`` hex prefix."""
    text = text.strip()
    if text.startswith("$"):
        return int(text[1:], 16)
    if text.startswith("-$"):
        return -int(text[2:], 16)
    return int(round(float(text)))


def as_float(text: str) -> float:
    text = text.strip()
    if text.startswith("$") or text.startswith("-$"):
        return float(as_int(text))
    return float(text)


def as_bool(text: str) -> bool:
    return as_int(text) != 0


def lines(text: str) -> list[str]:
    """Split a multi-line reply, dropping blanks."""
    return [line for line in (l.strip() for l in text.split("\n")) if line]


def status_words(text: str, count: int = 2, width: int = 6) -> list[int]:
    """Split a hex status reply into its fixed-width words.

    ``#1?`` returns twelve characters as two 24-bit words; ``???`` returns
    twelve as two words as well. Each character carries four bits, most
    significant first.
    """
    text = text.strip().replace(" ", "")
    expected = count * width
    if len(text) != expected:
        raise ValueError(f"expected {expected} hex characters, got {text!r}")
    return [int(text[i * width:(i + 1) * width], 16) for i in range(count)]
