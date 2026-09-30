# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
from siliconcompiler.utils import units
import pytest
from siliconcompiler.utils.units import \
    convert, \
    get_si_prefix, get_si_power, is_base_si_unit_power, \
    format_si, format_time, format_duration


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


@pytest.mark.parametrize("value,unit,expect", [
    (0, "B", (0.0, "")),
    (1023, "B", (1023.0, "")),
    (1024, "B", (1.0, "k")),
    (1536, "B", (1.5, "k")),
    (2**20, "B", (1.0, "M")),
    (2**30, "B", (1.0, "G")),
    (2**80, "B", (1.0, "Y")),
    (2**90, "B", (1024.0, "Y")),
    (-1536, "B", (-1.5, "k")),
    (-2**30, "B", (-1.0, "G")),
    (2048, "b", (2.0, "k")),
    (2048, "MB", (2048.0, "")),
    (2048, None, (2048.0, "")),
])
def test_scale_binary(value, unit, expect):
    assert units.scale_binary(value, unit) == expect


@pytest.mark.parametrize("value,expect", [
    (1024, "1.000k"),
    (2**30, "1.000G"),
    (-5000, "-4.883k"),
    (2**80, "1.000Y"),
    (2**90, "1024.000Y"),
])
def test_binary_boundaries(value, expect):
    assert units.format_binary(value, "B") == expect


@pytest.mark.parametrize("value,unit,expect", [
    (12, "B", "12.000 B"),
    (1536, "B", "1.500 KiB"),
    (1.5 * 2**30, "B", "1.500 GiB"),
    (2**80, "B", "1.000 YiB"),
    (-1536, "B", "-1.500 KiB"),
    (2048, "b", "2.000 Kib"),
    (1.5, "GB", "1.500 GB"),
    (1.5, None, "1.500"),
])
def test_binary_show_unit(value, unit, expect):
    assert units.format_binary(value, unit, show_unit=True) == expect


@pytest.mark.parametrize("value,unit,expect", [
    (12, "B", "12"),
    (1023, "B", "1023"),
    (1536, "B", "1.5k"),
    (99.94 * 2**20, "B", "99.9M"),
    (100 * 2**20, "B", "100M"),
    (1004.7 * 2**20, "B", "1005M"),
    (-200 * 2**10, "B", "-200k"),
    (1.5, "GB", "1.5"),
    (150.4, "GB", "150"),
])
def test_binary_compact(value, unit, expect):
    assert units.format_binary(value, unit, digits=1, compact=True) == expect


@pytest.mark.parametrize("value", [
    None,
    "",
    "abc",
    [],
    float("nan"),
    float("inf"),
    float("-inf"),
])
def test_binary_default(value):
    assert units.format_binary(value, "B", default="—") == "—"


@pytest.mark.parametrize("value,error", [
    (None, TypeError),
    ("abc", ValueError),
])
def test_binary_invalid_raises_without_default(value, error):
    with pytest.raises(error):
        units.format_binary(value, "B")


@pytest.mark.parametrize("value,expect", [
    (None, "—"),
    ("nonsense", "—"),
    (0, "0 B"),
    (12, "12 B"),
    (1023, "1023 B"),
    (1024, "1.0 KiB"),
    (1536, "1.5 KiB"),
    (-5000, "-4.9 KiB"),
    (104857600, "100 MiB"),
    (1073741824, "1.0 GiB"),
    (10737418240, "10.0 GiB"),
    (1053818880, "1005 MiB"),
    (2**80, "1.0 YiB"),
])
def test_binary_readable(value, expect):
    '''All the flags together: a size as a person reads it.'''
    assert units.format_binary(value, "B", digits=1, show_unit=True, compact=True,
                               default="—") == expect


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


@pytest.mark.parametrize("sec,milliseconds_digits,expect", [
    # Test milliseconds carrying to seconds
    (59.99951, 3, '1:00.000'),
    (0.99951, 3, '0:01.000'),
    (19.99951, 3, '0:20.000'),
    # Test seconds carrying to minutes (milliseconds_digits=0)
    (59.6, 0, '1:00'),
    (119.6, 0, '2:00'),
    # Test seconds carrying to minutes (with milliseconds)
    (59.99951, 1, '1:00.0'),
    (59.99951, 2, '1:00.00'),
    # Test minutes carrying to hours
    (59 * 60 + 59.6, 0, '1:00:00'),
    (59 * 60 + 59.99951, 3, '1:00:00.000'),
    # Test full overflow chain: hours:minutes:seconds
    (59 * 3600 + 59 * 60 + 59.99951, 3, '60:00:00.000'),
    (23 * 3600 + 59 * 60 + 59.6, 0, '24:00:00'),
])
def test_format_time_rounding_carry(sec, milliseconds_digits, expect):
    """Test that rounding properly propagates carries across time units."""
    assert format_time(sec, milliseconds_digits=milliseconds_digits) == expect


@pytest.mark.parametrize("sec,expect", [
    (0, "0s"),
    (42, "42s"),
    (59, "59s"),
    (60, "1m 00s"),
    (7 * 60 + 12, "7m 12s"),
    (59 * 60 + 59, "59m 59s"),
    (3600, "1h 00m"),
    (3 * 3600 + 5 * 60 + 59, "3h 05m"),
    (23 * 3600 + 59 * 60 + 59, "23h 59m"),
    (24 * 3600, "1d 00h"),
    (2 * 86400 + 6 * 3600 + 59 * 60, "2d 06h"),
    (400 * 86400, "400d 00h"),
])
def test_format_duration(sec, expect):
    assert format_duration(sec) == expect


@pytest.mark.parametrize("sec,expect", [
    (59.9, "59s"),
    (60.999, "1m 00s"),
    (3599.9, "59m 59s"),
])
def test_format_duration_truncates(sec, expect):
    assert format_duration(sec) == expect


@pytest.mark.parametrize("sec,expect", [
    ("42", "42s"),
    ("90.5", "1m 30s"),
])
def test_format_duration_numeric_string(sec, expect):
    assert format_duration(sec) == expect


@pytest.mark.parametrize("sec", [
    None,
    -1,
    -3600,
    "",
    "abc",
    float("nan"),
    float("inf"),
    float("-inf"),
    [],
    object(),
])
def test_format_duration_invalid(sec):
    assert format_duration(sec) == "—"
