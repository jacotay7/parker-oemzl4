import pytest

from parker_oemzl4 import units


def test_length_conversions():
    assert units.to_cm(1, "cm") == 1.0
    assert units.to_cm(10, "mm") == pytest.approx(1.0)
    assert units.to_cm(1, "m") == pytest.approx(100.0)
    assert units.to_cm(1, "in") == pytest.approx(2.54)
    assert units.to_cm(10000, "um") == pytest.approx(1.0)


def test_round_trip_length():
    for unit in ("cm", "mm", "m", "um", "in"):
        assert units.from_cm(units.to_cm(3.5, unit), unit) == pytest.approx(3.5)


def test_unknown_length_unit():
    with pytest.raises(ValueError, match="unknown length unit"):
        units.to_cm(1, "furlong")


def test_length_to_counts():
    assert units.length_to_counts(1, "cm", 5000) == pytest.approx(5000)
    assert units.length_to_counts(1, "mm", 5000) == pytest.approx(500)


def test_counts_to_length():
    assert units.counts_to_length(5000, "cm", 5000) == pytest.approx(1.0)
    assert units.counts_to_length(500, "mm", 5000) == pytest.approx(1.0)


def test_counts_to_length_rejects_zero_scale():
    with pytest.raises(ValueError):
        units.counts_to_length(100, "cm", 0)


def test_speed_to_ixx22_counts_per_msec():
    # Ixx22 is counts/msec: 1 cm/s at 5000 counts/cm is 5000 counts/s = 5/msec.
    assert units.speed_to_counts_per_msec(1, "cm/s", 5000) == pytest.approx(5.0)
    assert units.speed_to_counts_per_msec(1, "mm/s", 5000) == pytest.approx(0.5)


def test_speed_per_minute():
    assert units.speed_to_counts_per_msec(60, "cm/min", 5000) == pytest.approx(5.0)


def test_speed_round_trip():
    per_msec = units.speed_to_counts_per_msec(2.5, "mm/s", 4321)
    back = units.counts_per_msec_to_speed(per_msec, "mm/s", 4321)
    assert back == pytest.approx(2.5)


def test_bad_rate_units():
    with pytest.raises(ValueError, match="not a rate unit"):
        units.speed_to_counts_per_msec(1, "cm", 5000)
    with pytest.raises(ValueError, match="unknown time unit"):
        units.speed_to_counts_per_msec(1, "cm/fortnight", 5000)
