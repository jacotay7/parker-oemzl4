"""Exceptions raised by the Turbo PMAC library."""


class PMACError(Exception):
    """Base class for every error this library raises."""


class TransportError(PMACError):
    """The link to the controller failed: not found, claimed, or timed out."""


class DeviceNotFound(TransportError):
    """No controller matched on the bus."""


class CommandError(PMACError):
    """The controller answered with an error string.

    Turbo PMAC prefixes an error reply with <BEL> and reports it as ``ERRnnn``.
    ``code`` is the numeric part when one could be parsed.
    """

    def __init__(self, command: str, reply: str, code: int | None = None):
        self.command = command
        self.reply = reply
        self.code = code
        detail = f" ({ERROR_MEANINGS[code]})" if code in ERROR_MEANINGS else ""
        super().__init__(f"{command!r} -> {reply}{detail}")


# From the Turbo PMAC Software Reference, "Communications Error Codes".
ERROR_MEANINGS = {
    1: "command not allowed while program is running",
    2: "password error",
    3: "data error or unrecognised command",
    4: "illegal character: bad value or invalid format",
    5: "command not allowed unless buffer is open",
    6: "no room in buffer for command",
    7: "buffer already in use",
    8: "MACRO auxiliary communications error",
    9: "program structural error, e.g. ENDIF without IF",
    10: "both overtravel limits set for a motor in the C.S.",
    11: "previous move not completed",
    12: "a motor in the coordinate system is open-loop",
    13: "a motor in the coordinate system is not activated",
    14: "no motors in the coordinate system",
    15: "not pointing to valid program buffer",
    16: "running improperly structured program",
    17: "trying to resume after H or Q with motors out of position",
    18: "attempt to perform phase reference during move",
    19: "illegal position-change command while moves stored in CCBUFFER",
}
