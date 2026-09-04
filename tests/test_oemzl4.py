import pytest

from parker_oemzl4 import OEMZL4Axis, drive
from turbo_pmac import PMAC, FakeTransport


def axis(replies, **kwargs):
    pmac = PMAC(FakeTransport(replies))
    return OEMZL4Axis(pmac.motor(1), channel=1, **kwargs)


# -- reference data --------------------------------------------------------

def test_pinout_matches_the_manual():
    assert drive.PINOUT[1] == "STEP+"
    assert drive.PINOUT[14] == "STEP-"
    assert drive.PINOUT[9] == "FLT C"
    assert drive.PINOUT[21] == "FLT E"


def test_step_input_is_a_5v_interface():
    assert drive.STEP.accepts(5.0)
    assert not drive.STEP.accepts(12.0)  # 5.2 V absolute maximum
    assert not drive.STEP.accepts(3.0)   # 3.5 V minimum for a logic high


def test_shutdown_tolerates_more_than_step_does():
    assert drive.SHUTDOWN.accepts(12.0)


def test_resolution_and_current_tables():
    assert drive.steps_per_rev(0) == 200
    assert drive.steps_per_rev(15) == 50800
    assert drive.current_amps(0) == pytest.approx(0.14)
    assert drive.current_amps(31) == pytest.approx(4.00)


def test_switch_codes_are_range_checked():
    with pytest.raises(ValueError):
        drive.steps_per_rev(16)
    with pytest.raises(ValueError):
        drive.current_amps(32)


def test_max_speed_follows_the_2mhz_ceiling():
    assert drive.max_speed_rps(25000) == pytest.approx(80.0)


def test_check_step_rate_rejects_over_2mhz():
    drive.check_step_rate(2_000_000)
    with pytest.raises(ValueError):
        drive.check_step_rate(2_000_001)


# -- axis configuration checks ---------------------------------------------

# $078004 is channel 1's C output, which is the register PFM is emitted from.
GOOD = {"I7016": "3", "I102": "$78004", "#1?": "880000000000"}
# The state this controller was found in: PWM carrier, and the motor pointed at
# the A output register, so no pulses were ever emitted.
AS_FOUND = {"I7016": "0", "I102": "$78002", "#1?": "850000000000"}


def test_pwm_output_mode_is_reported_as_a_problem():
    check = axis(AS_FOUND).check_configuration()
    assert not check.ok
    assert any("PWM" in problem for problem in check.problems)


def test_pfm_output_mode_passes():
    assert axis(GOOD).check_configuration().ok


def test_enable_refuses_while_the_channel_is_in_pwm_mode():
    with pytest.raises(RuntimeError, match="refusing to enable"):
        axis(AS_FOUND).enable()


def test_enable_proceeds_when_configured():
    a = axis(GOOD)
    a.enable()
    assert "#1J/" in a.motor.pmac.transport.sent


def test_channel_maps_to_the_right_servo_ic_variables():
    pmac = PMAC(FakeTransport({"I7126": "3"}))
    a = OEMZL4Axis(pmac.motor(2), channel=6)
    assert a.output_mode == 3  # channel 6 -> servo IC 1, channel 2


def test_c_output_addresses_follow_the_servo_ic_layout():
    from parker_oemzl4 import c_output_address
    # Channels are 8 addresses apart; the C output sits at base+4.
    assert c_output_address(1) == 0x078004
    assert c_output_address(2) == 0x07800C
    assert c_output_address(4) == 0x07801C
    assert c_output_address(5) == 0x078104   # servo IC 1
    assert c_output_address(8) == 0x07811C


def test_wrong_output_register_is_a_problem():
    # Pointing the motor at the A output emits no pulses at all, silently.
    check = axis({"I7016": "2", "I102": "$78002", "#1?": "880000000000"}).check_configuration()
    assert not check.ok
    assert any("C output" in p for p in check.problems)


def test_units_need_a_scale_factor():
    a = axis(GOOD)
    with pytest.raises(ValueError, match="counts_per_cm is unknown"):
        a.to_counts(1, "cm")


def test_move_by_converts_to_counts():
    a = axis(GOOD, counts_per_cm=5000)
    assert a.to_counts(1, "cm") == pytest.approx(5000)
    assert a.to_counts(1, "mm") == pytest.approx(500)
    assert a.to_length(2500, "mm") == pytest.approx(5.0)


def test_set_speed_writes_ixx22_in_counts_per_msec():
    a = axis(GOOD, counts_per_cm=5000)
    assert a.set_speed(1, "cm/s") == pytest.approx(5.0)
    assert "I122=5.0" in a.motor.pmac.transport.sent


def test_set_speed_rejects_beyond_the_drive_step_rate():
    a = axis(GOOD, counts_per_cm=5000, resolution=25000)
    with pytest.raises(ValueError):
        a.set_speed(1000, "cm/s")


def test_channel_is_range_checked():
    pmac = PMAC(FakeTransport({}))
    with pytest.raises(ValueError):
        OEMZL4Axis(pmac.motor(1), channel=9)


def test_speed_check_needs_a_known_resolution():
    with pytest.raises(ValueError, match="resolution is unknown"):
        axis(GOOD).check_speed_rps(1.0)


def test_speed_check_uses_the_configured_resolution():
    a = axis(GOOD, resolution=25000)
    a.check_speed_rps(80.0)
    with pytest.raises(ValueError):
        a.check_speed_rps(81.0)
