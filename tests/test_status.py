from turbo_pmac.status import MotorStatus

# The state the Brick was found in: activated, but killed and open loop.
AS_FOUND = "850000000000"


def test_parses_the_real_as_found_status():
    status = MotorStatus.parse(AS_FOUND)
    assert status.activated is True
    assert status.amplifier_enabled is False
    assert status.open_loop is True
    assert status.integration_mode is True
    assert status.move_timer_active is False


def test_killed_is_derived_from_amplifier_enabled():
    status = MotorStatus.parse(AS_FOUND)
    assert status.killed is True
    assert status.closed_loop is False
    assert status.faulted is False


def test_summary_describes_the_state():
    assert "killed" in MotorStatus.parse(AS_FOUND).summary()


def test_closed_loop_when_enabled_and_not_open_loop():
    # bit 23 activated + bit 19 amplifier enabled, bit 18 clear.
    status = MotorStatus.parse("880000000000")
    assert status.amplifier_enabled is True
    assert status.open_loop is False
    assert status.closed_loop is True
    assert status.killed is False


def test_limit_flags_decode():
    status = MotorStatus.parse("E00000000000")  # bits 23, 22, 21
    assert status.activated
    assert status.negative_limit_set
    assert status.positive_limit_set


def test_second_word_fault_bits():
    status = MotorStatus.parse("000000000004")  # bit 2 of second word
    assert status.fatal_following_error is True
    assert status.faulted is True


def test_in_position_bit():
    assert MotorStatus.parse("000000000001").in_position is True


def test_active_flags_lists_only_set_bits():
    flags = MotorStatus.parse(AS_FOUND).active_flags()
    assert set(flags) == {"activated", "open_loop", "integration_mode"}
