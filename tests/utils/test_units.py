# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
from siliconcompiler.utils import units
import pytest
from siliconcompiler.utils.units import \
    convert, \
    get_si_prefix, get_si_power, is_base_si_unit_power, \
    format_si, format_time


@pytest.mark.parametrize("value,unit,expect", [
    (1.5 * 1024 * 1024 * 1024, "B", "1.500G"),
])
def test_binary_default_digits(value, unit, expect):
    assert units.format_binary(value, unit) == expect


@pytest.mark.parametrize("value,unit,digits,expect", [
    (1.5 * 1024 * 1024 * 1024, "B", 1, "1.5G"),
    (1.5, "GB", 3, "1.500"),
    (1.5, "GB", 1, "1.5"),
])
def test_binary_with_digits(value, unit, digits, expect):
    assert units.format_binary(value, unit, digits=digits) == expect


@pytest.mark.parametrize("sec,expect", [
    (6 * 3600 + 35 * 60 + 20 + 0.04, '6:35:20.040'),
    (36 * 3600 + 35 * 60 + 20 + 0.04, '36:35:20.040'),
    (35 * 60 + 20 + 0.05, '35:20.050'),
    (20 + 0.05, '0:20.050'),
    (20 + 0.6508, '0:20.651'),
])
def test_time(sec, expect):
    assert units.format_time(sec) == expect


@pytest.mark.parametrize("sec,expect,digits", [
    (6 * 3600 + 35 * 60 + 20 + 0.04, '6:35:20', 0),
    (36 * 3600 + 35 * 60 + 20 + 0.04, '36:35:20', 0),
    (35 * 60 + 20 + 0.05, '35:20', 0),
    (20 + 0.05, '0:20', 0),
    (20 + 0.6508, '0:21', 0),
    (6 * 3600 + 35 * 60 + 20 + 0.04, '6:35:20.0', 1),
    (36 * 3600 + 35 * 60 + 20 + 0.04, '36:35:20.0', 1),
    (35 * 60 + 20 + 0.05, '35:20.1', 1),
    (20 + 0.05, '0:20.1', 1),
    (20 + 0.6508, '0:20.7', 1),
    (6 * 3600 + 35 * 60 + 20 + 0.04, '6:35:20.04', 2),
    (36 * 3600 + 35 * 60 + 20 + 0.04, '36:35:20.04', 2),
    (35 * 60 + 20 + 0.05, '35:20.05', 2),
    (20 + 0.05, '0:20.05', 2),
    (20 + 0.6508, '0:20.65', 2),
    (6 * 3600 + 35 * 60 + 20 + 0.04, '6:35:20.040', 3),
    (36 * 3600 + 35 * 60 + 20 + 0.04, '36:35:20.040', 3),
    (35 * 60 + 20 + 0.05, '35:20.050', 3),
    (20 + 0.05, '0:20.050', 3),
    (20 + 0.6508, '0:20.651', 3)
])
def test_time_milliseconds(sec, expect, digits):
    assert units.format_time(sec, milliseconds_digits=digits) == expect


@pytest.mark.parametrize("value,unit,expect", [
    (1e5, 'Hz', '100.000k'),
    (1.1e9, 'Hz', '1.100G'),
    (1e5, 'kHz', '100000.000'),
])
def test_si_default(value, unit, expect):
    assert units.format_si(value, unit) == expect


@pytest.mark.parametrize("value,unit,digits,expect", [
    (1e5, 'Hz', 0, '100k'),
])
def test_si_with_digits(value, unit, digits, expect):
    assert units.format_si(value, unit, digits=digits) == expect


@pytest.mark.parametrize("value,unit,margin,expect", [
    (1e5, 'Hz', 0, '0.100M'),
])
def test_si_with_margin(value, unit, margin, expect):
    assert units.format_si(value, unit, margin=margin) == expect


@pytest.mark.parametrize("value,from_unit,to_unit,expect", [
    (1555, 'um', 'mm', 1.555),
    (1, 'um', 'mm', 0.001),
    (1555, 'mm', 'um', 1555000),
    (1, 'mm', 'um', 1000),
])
def test_si_with_um_to_mm(value, from_unit, to_unit, expect):
    assert units.convert(value, from_unit=from_unit, to_unit=to_unit) == expect


@pytest.mark.parametrize("value,from_unit,to_unit,expect", [
    (1555, 'um^2', 'mm^2', 0.001555),
    (1, 'um^2', 'mm^2', 1e-6),
    (1555, 'mm^2', 'um^2', 1555e6),
    (1, 'mm^2', 'um^2', 1e6),
])
def test_si_with_um2_to_mm2(value, from_unit, to_unit, expect):
    assert units.convert(value, from_unit=from_unit, to_unit=to_unit) == expect


@pytest.mark.parametrize("value,to_unit,expect", [
    (1555, 'mm', 1555e3),
    (1, 'mm', 1e3),
])
def test_si_with_none_to_mm(value, to_unit, expect):
    assert units.convert(value, to_unit=to_unit) == expect


@pytest.mark.parametrize("value,to_unit,expect", [
    (1555, 'mm^2', 1555e6),
    (1, 'mm^2', 1e6),
])
def test_si_with_none_to_mm2(value, to_unit, expect):
    assert units.convert(value, to_unit=to_unit) == expect


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
    (0.2, "0:00.200"),
    (2, "0:02.000"),
    (20, "0:20.000"),
    (200, "3:20.000"),
    (2000, "33:20.000"),
    (2e4, "5:33:20.000"),
    (2e5, "55:33:20.000"),
    (2e6, "555:33:20.000"),
])
def test_format_time(value, expect):
    assert format_time(value) == expect
