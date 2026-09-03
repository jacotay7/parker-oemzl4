import pytest

from turbo_pmac import response
from turbo_pmac.errors import CommandError


def test_clean_strips_ack_and_carriage_return():
    text, error = response.clean(b"1.947  \r\x06")
    assert text == "1.947"
    assert error is False


def test_clean_drops_nul_padding():
    # The USB transport answers NUL when nothing is ready; it never means data.
    text, error = response.clean(b"\x00\x00" + b"TURBO2, X4\r" + b"\x00")
    assert text == "TURBO2, X4"
    assert error is False


def test_clean_flags_bel_as_error():
    text, error = response.clean(b"\x07ERR003\r")
    assert text == "ERR003"
    assert error is True


def test_check_raises_with_decoded_meaning():
    with pytest.raises(CommandError) as excinfo:
        response.check("I9999", "ERR003", True)
    assert excinfo.value.code == 3
    assert "unrecognised command" in str(excinfo.value)


def test_check_passes_through_success():
    assert response.check("VERSION", "1.947", False) == "1.947"


@pytest.mark.parametrize("text, expected", [
    ("2000", 2000),
    ("$78002", 0x78002),
    ("-$10", -0x10),
    ("-5797.53125", -5798),
])
def test_as_int(text, expected):
    assert response.as_int(text) == expected


def test_as_float_handles_hex_and_decimal():
    assert response.as_float("-5797.53125") == pytest.approx(-5797.53125)
    assert response.as_float("$3501") == pytest.approx(float(0x3501))


def test_status_words_splits_two_24_bit_words():
    assert response.status_words("850000000000") == [0x850000, 0x000000]


def test_status_words_rejects_wrong_length():
    with pytest.raises(ValueError):
        response.status_words("8500")
