# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
from siliconcompiler import units


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
