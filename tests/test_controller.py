import pytest

from turbo_pmac import PMAC, FakeError, FakeTransport
from turbo_pmac.errors import CommandError
from turbo_pmac.protocol import CTRL_DISABLE_PLCS, CTRL_KILL_ALL


def make(replies=None, **kwargs):
    transport = FakeTransport(replies or {}, **kwargs)
    return PMAC(transport), transport


def test_command_returns_reply():
    pmac, _ = make({"VERSION": "1.947"})
    assert pmac.version == "1.947"


def test_reply_survives_ack_arriving_on_a_later_read():
    # The device answers the terminating ACK several reads after the text.
    pmac, _ = make({"VERSION": "1.947"}, ack_delay=5)
    assert pmac.version == "1.947"


def test_stale_ack_does_not_swallow_the_next_reply():
    # A leftover ACK from an earlier command must not end this one early;
    # ignoring that is what kept every later command aligned on real hardware.
    pmac, _ = make({"TYPE": "TURBO2, X4"}, stale_ack=True)
    assert pmac.card_type == "TURBO2, X4"


def test_commands_stay_aligned_across_a_sequence():
    pmac, _ = make({"VERSION": "1.947", "TYPE": "TURBO2, X4", "#1P": "-5797.53125"})
    assert pmac.version == "1.947"
    assert pmac.card_type == "TURBO2, X4"
    assert pmac.command("#1P") == "-5797.53125"


def test_error_reply_raises():
    pmac, _ = make({"I9999": FakeError("ERR003")})
    with pytest.raises(CommandError):
        pmac.get("I9999")


def test_get_int_accepts_hex():
    pmac, _ = make({"I102": "$78002"})
    assert pmac.get_int("I102") == 0x78002


def test_set_formats_assignment():
    pmac, transport = make()
    pmac.set("I7016", 3)
    assert "I7016=3" in transport.sent


def test_emergency_stop_disables_plcs_before_killing():
    pmac, transport = make()
    pmac.emergency_stop()
    assert transport.sent == [CTRL_DISABLE_PLCS, CTRL_KILL_ALL]


def test_motor_addresses_are_prefixed():
    pmac, transport = make({"#2P": "10.0"})
    assert pmac.motor(2).position == 10.0
    assert "#2P" in transport.sent


def test_motor_ivar_builds_the_right_name():
    pmac, transport = make({"I130": "2000"})
    assert pmac.motor(1).ivar(30) == "2000"
    assert "I130" in transport.sent


def test_motor_number_is_validated():
    pmac, _ = make()
    with pytest.raises(ValueError):
        pmac.motor(0)


def test_close_closes_the_transport():
    pmac, transport = make()
    with pmac:
        pass
    assert transport.closed is True
