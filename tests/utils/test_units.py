import pytest
from siliconcompiler.units import \
    convert, \
    get_si_prefix, get_si_power, is_base_si_unit_power, \
    format_si, format_time


@pytest.mark.parametrize("value,from_unit,to_unit,correct", [
    (1.0, None, None, 1.0),
    (1.0, "nm", "m", 1.0e-9),
    (1.0, "m", "um", 1.0e6),
    (1.0, "ms", "ms", 1.0),
    (1.0, "m^2", "um^2", 1.0e12),
])
def test_convert(value, from_unit, to_unit, correct):
    assert convert(value, from_unit=from_unit, to_unit=to_unit) == correct


@pytest.mark.parametrize("unit,scale", [
    ("nm", "n"),
    (None, ""),
    ("Pm", "P"),
    ("kilo", "kilo"),
])
def test_get_si_prefix(unit, scale):
    assert get_si_prefix(unit) == scale


@pytest.mark.parametrize("unit,scale", [
    ('um', 1),
    ('', 1),
    ('um^2', 2),
    ('um^3', 3)
])
def test_get_si_power(unit, scale):
    assert get_si_power(unit) == scale


@pytest.mark.parametrize("unit,expect", [
    ('um', False),
    ('', False),
    ('um^2', True),
    ('um^3', True)
])
def test_is_base_si_unit_power(unit, expect):
    assert is_base_si_unit_power(unit) is expect


@pytest.mark.parametrize("value,unit,margin,digits,expect", [
    (2.050, 'um', 3, 3, "2.050"),
    (2.050, 'um', 3, 1, "2.0"),
    (2.050, 'um', 3, -1, "2.0"),
    (2.050e-6, 'm', 3, 3, "2.050u"),
    (2.050e-6, 'm', 4, 3, "2050.000n"),
    (2.050e-9, 'm', 3, 1, "2.0n"),
    (2.050e-12, 'm', 3, -1, "2.0p"),
    (2.050e25, 'm', 0, 1, "20499999999999998313889792.0"),
])
def test_format_si(value, unit, margin, digits, expect):
    assert format_si(value, unit, margin=margin, digits=digits) == expect


@pytest.mark.parametrize("value,expect", [
    (0.2, "00.200"),
    (2, "02.000"),
    (20, "20.000"),
    (200, "03:20.000"),
    (2000, "33:20.000"),
    (2e4, "5:33:20.000"),
    (2e5, "55:33:20.000"),
    (2e6, "555:33:20.000"),
])
def test_format_time(value, expect):
    assert format_time(value) == expect
