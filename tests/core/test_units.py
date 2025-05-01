# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
from siliconcompiler.utils import units
import pytest
from siliconcompiler.utils.units import \
    convert, \
    get_si_prefix, get_si_power, is_base_si_unit_power, \
    format_si, format_time


def test_binary():
    GB = 1.5
    value = GB * 1024 * 1024 * 1024
    assert units.format_binary(value, 'B') == "1.500G"
    assert units.format_binary(value, 'B', digits=1) == "1.5G"

    assert units.format_binary(GB, 'GB', digits=3) == "1.500"
    assert units.format_binary(GB, 'GB', digits=1) == "1.5"


def test_time():
    sec = 6 * 3600 + 35 * 60 + 20 + 0.04
    assert units.format_time(sec) == '6:35:20.040'
    sec = 36 * 3600 + 35 * 60 + 20 + 0.04
    assert units.format_time(sec) == '36:35:20.040'
    sec = 35 * 60 + 20 + 0.05
    assert units.format_time(sec) == '35:20.050'
    sec = 20 + 0.05
    assert units.format_time(sec) == '20.050'


def test_si():
    value = 1e5
    assert units.format_si(value, 'Hz') == '100.000k'
    assert units.format_si(value, 'Hz', digits=0) == '100k'
    assert units.format_si(value, 'Hz', margin=0) == '0.100M'

    assert units.format_si(1.1e9, 'Hz') == '1.100G'

    assert units.format_si(value, 'kHz') == '100000.000'


def test_si_with_um_to_mm():
    assert units.convert(1555, from_unit='um', to_unit='mm') == 1.555
    assert units.convert(1, from_unit='um', to_unit='mm') == 0.001

    assert units.convert(1555, from_unit='mm', to_unit='um') == 1555000
    assert units.convert(1, from_unit='mm', to_unit='um') == 1000


def test_si_with_um2_to_mm2():
    assert units.convert(1555, from_unit='um^2', to_unit='mm^2') == 0.001555
    assert units.convert(1, from_unit='um^2', to_unit='mm^2') == 1e-6

    assert units.convert(1555, from_unit='mm^2', to_unit='um^2') == 1555e6
    assert units.convert(1, from_unit='mm^2', to_unit='um^2') == 1e6


def test_si_with_none_to_mm():
    assert units.convert(1555, to_unit='mm') == 1555e3
    assert units.convert(1, to_unit='mm') == 1e3


def test_si_with_none_to_mm2():
    assert units.convert(1555, to_unit='mm^2') == 1555e6
    assert units.convert(1, to_unit='mm^2') == 1e6


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
