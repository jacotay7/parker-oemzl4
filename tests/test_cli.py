import pytest

from parker_oemzl4.cli import allow_negative_quantities, build_parser, parse_quantity


@pytest.mark.parametrize("text, expected", [
    ("1cm", (1.0, "cm")),
    ("1 cm", (1.0, "cm")),
    ("-5mm", (-5.0, "mm")),
    ("+2.5 in", (2.5, "in")),
    ("0.001m", (0.001, "m")),
    ("1e3um", (1000.0, "um")),
])
def test_parse_quantity_with_unit(text, expected):
    assert parse_quantity(text, "mm") == expected


def test_parse_quantity_falls_back_to_default_unit():
    assert parse_quantity("7", "mm") == (7.0, "mm")


def test_parse_quantity_handles_rates():
    assert parse_quantity("30mm/min", "cm/s") == (30.0, "mm/min")


def test_parse_quantity_rejects_nonsense():
    with pytest.raises(ValueError):
        parse_quantity("over there", "mm")


def test_parser_accepts_the_documented_commands():
    parser = build_parser()
    assert parser.parse_args(["status"]).action == "status"
    assert parser.parse_args(["move", "1cm"]).distance == "1cm"
    assert parser.parse_args(["moveto", "2cm"]).action == "moveto"
    assert parser.parse_args(["zero"]).action == "zero"
    assert parser.parse_args(["stop"]).action == "stop"


def test_parser_requires_an_action():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_negative_quantities_survive_argparse():
    # "-5mm" looks like an option flag to argparse; argparse only exempts bare
    # negative numbers. Without the shim this raises SystemExit.
    argv = allow_negative_quantities(["move", "-5mm", "--speed", "2mm/s"])
    args = build_parser().parse_args(argv)
    assert args.action == "move"
    assert parse_quantity(args.distance, "mm") == (-5.0, "mm")
    assert args.speed == "2mm/s"


def test_negative_rate_survives_argparse():
    argv = allow_negative_quantities(["speed", "-1.5cm/s"])
    assert parse_quantity(build_parser().parse_args(argv).value, "cm/s") == (-1.5, "cm/s")


def test_real_option_flags_are_untouched():
    assert allow_negative_quantities(["move", "1cm", "--speed", "2mm/s"]) == [
        "move", "1cm", "--speed", "2mm/s"]
    assert allow_negative_quantities(["--help"]) == ["--help"]
