"""Decode Turbo PMAC status words.

Bit assignments are transcribed from the Turbo PMAC/PMAC2 Software Reference,
"Turbo PMAC On-Line Command Specification", for the ``?`` (motor status) and
``??`` / ``???`` (global status) commands.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from .response import status_words

# Motor status, first word (X:$0000B0 for motor 1).
_MOTOR_WORD_1 = {
    23: "activated",
    22: "negative_limit_set",
    21: "positive_limit_set",
    20: "extended_servo_algorithm",
    19: "amplifier_enabled",
    18: "open_loop",
    17: "move_timer_active",
    16: "integration_mode",
    15: "dwell_in_progress",
    14: "data_block_error",
    13: "desired_velocity_zero",
    12: "abort_deceleration",
    11: "block_request",
    10: "home_search_in_progress",
    9: "user_phase_enable",
    8: "user_servo_enable",
    7: "alternate_source_destination",
    6: "phased_motor",
    5: "following_offset_mode",
    4: "following_enabled",
    3: "error_trigger",
    2: "software_position_capture",
    1: "alternate_command_output_mode",
    0: "maximum_rapid_speed",
}

# Motor status, second word (Y:$0000C0 for motor 1). Bits 23-16 are two
# multi-bit fields rather than flags and are decoded separately.
_MOTOR_WORD_2 = {
    15: "assigned_to_coordinate_system",
    13: "foreground_in_position",
    12: "stopped_on_desired_position_limit",
    11: "stopped_on_position_limit",
    10: "home_complete",
    9: "phasing_search_active",
    8: "phasing_reference_error",
    7: "trigger_move",
    6: "integrated_fatal_following_error",
    5: "i2t_amplifier_fault",
    4: "backlash_direction",
    3: "amplifier_fault",
    2: "fatal_following_error",
    1: "warning_following_error",
    0: "in_position",
}


@dataclass(frozen=True)
class MotorStatus:
    """Decoded reply to ``#n?``."""

    raw: str
    word1: int
    word2: int

    # First word
    activated: bool = False
    negative_limit_set: bool = False
    positive_limit_set: bool = False
    extended_servo_algorithm: bool = False
    amplifier_enabled: bool = False
    open_loop: bool = False
    move_timer_active: bool = False
    integration_mode: bool = False
    dwell_in_progress: bool = False
    data_block_error: bool = False
    desired_velocity_zero: bool = False
    abort_deceleration: bool = False
    block_request: bool = False
    home_search_in_progress: bool = False
    user_phase_enable: bool = False
    user_servo_enable: bool = False
    alternate_source_destination: bool = False
    phased_motor: bool = False
    following_offset_mode: bool = False
    following_enabled: bool = False
    error_trigger: bool = False
    software_position_capture: bool = False
    alternate_command_output_mode: bool = False
    maximum_rapid_speed: bool = False

    # Second word
    assigned_to_coordinate_system: bool = False
    foreground_in_position: bool = False
    stopped_on_desired_position_limit: bool = False
    stopped_on_position_limit: bool = False
    home_complete: bool = False
    phasing_search_active: bool = False
    phasing_reference_error: bool = False
    trigger_move: bool = False
    integrated_fatal_following_error: bool = False
    i2t_amplifier_fault: bool = False
    backlash_direction: bool = False
    amplifier_fault: bool = False
    fatal_following_error: bool = False
    warning_following_error: bool = False
    in_position: bool = False

    coordinate_system: int = 0
    coordinate_definition: int = 0

    @classmethod
    def parse(cls, reply: str) -> "MotorStatus":
        word1, word2 = status_words(reply, count=2, width=6)
        flags = {name: bool(word1 >> bit & 1) for bit, name in _MOTOR_WORD_1.items()}
        flags.update({name: bool(word2 >> bit & 1) for bit, name in _MOTOR_WORD_2.items()})
        return cls(
            raw=reply.strip(), word1=word1, word2=word2,
            coordinate_system=(word2 >> 20 & 0xF) + 1,
            coordinate_definition=word2 >> 16 & 0xF,
            **flags,
        )

    @property
    def killed(self) -> bool:
        """True when the motor's outputs are disabled.

        The controller has no single "killed" bit: a killed motor is one whose
        amplifier is not enabled. It may still be activated.
        """
        return not self.amplifier_enabled

    @property
    def closed_loop(self) -> bool:
        return self.amplifier_enabled and not self.open_loop

    @property
    def faulted(self) -> bool:
        return (self.amplifier_fault or self.fatal_following_error
                or self.integrated_fatal_following_error or self.i2t_amplifier_fault)

    def active_flags(self) -> list[str]:
        """Names of every flag currently set, for display."""
        skip = {"raw", "word1", "word2", "coordinate_system", "coordinate_definition"}
        return [f.name for f in fields(self)
                if f.name not in skip and getattr(self, f.name)]

    def summary(self) -> str:
        if not self.activated:
            state = "deactivated"
        elif self.killed:
            state = "killed (outputs disabled)"
        elif self.open_loop:
            state = "enabled, open loop"
        else:
            state = "enabled, closed loop"
        if self.faulted:
            state += " -- FAULT"
        return state
