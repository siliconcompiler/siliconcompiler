# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
from siliconcompiler.utils import asic
import pytest
from siliconcompiler.targets import freepdk45_demo, skywater130_demo


@pytest.mark.nostrict
def test_calc_area():

    chip = siliconcompiler.Chip('test')

    # Test rectangle
    chip.set('constraint', 'outline', [(0, 0), (10, 10)])
    assert asic.calc_area(chip) == 100.0

    # Test rectilinear shape
    chip.set('constraint', 'outline', [(0, 0), (0, 20), (10, 20), (10, 10), (20, 10), (20, 0)])
    assert asic.calc_area(chip) == 300.0


def test_calc_area_with_stepindex():
    chip = siliconcompiler.Chip('test')

    # Test rectangle
    chip.set('constraint', 'outline', [(0, 0), (10, 10)], step='floorplan', index='0')

    # Test rectilinear shape
    chip.set('constraint', 'outline', [(0, 0), (0, 20), (10, 20), (10, 10), (20, 10), (20, 0)],
             step='floorplan', index='1')

    assert asic.calc_area(chip, step='floorplan', index='0') == 100.0
    assert asic.calc_area(chip, step='floorplan', index='1') == 300.0


@pytest.mark.nostrict
def test_calc_dpw():

    chip = siliconcompiler.Chip('test')
    chip.load_target(skywater130_demo)

    chip.set('constraint', 'outline', [(0, 0), (150000, 75000)])
    assert asic.calc_dpw(chip) == 0

    chip.set('constraint', 'outline', [(0, 0), (75000, 75000)])
    assert asic.calc_dpw(chip) == 4

    chip.set('constraint', 'outline', [(0, 0), (5000, 5000)])
    assert asic.calc_dpw(chip) == 2520


def test_calc_dpw_with_stepindex():

    chip = siliconcompiler.Chip('test')
    chip.load_target(skywater130_demo)

    chip.set('constraint', 'outline', [(0, 0), (150000, 75000)], step='floorplan', index='0')
    chip.set('constraint', 'outline', [(0, 0), (75000, 75000)], step='floorplan', index='1')
    chip.set('constraint', 'outline', [(0, 0), (5000, 5000)], step='floorplan', index='2')

    assert asic.calc_dpw(chip, step='floorplan', index='0') == 0
    assert asic.calc_dpw(chip, step='floorplan', index='1') == 4
    assert asic.calc_dpw(chip, step='floorplan', index='2') == 2520


@pytest.mark.nostrict
def test_calc_yield_poisson():
    chip = siliconcompiler.Chip('test')
    chip.load_target(freepdk45_demo)

    chip.set('constraint', 'outline', [(0, 0), (150000, 75000)])
    assert int(1000 * asic.calc_yield(chip)) == 245

    chip.set('constraint', 'outline', [(0, 0), (75000, 75000)])
    assert int(1000 * asic.calc_yield(chip)) == 495

    chip.set('constraint', 'outline', [(0, 0), (5000, 5000)])
    assert int(1000 * asic.calc_yield(chip)) == 996


def test_calc_yield_poisson_with_stepindex():
    chip = siliconcompiler.Chip('test')
    chip.load_target(freepdk45_demo)

    chip.set('constraint', 'outline', [(0, 0), (150000, 75000)], step='floorplan', index='0')
    chip.set('constraint', 'outline', [(0, 0), (75000, 75000)], step='floorplan', index='1')
    chip.set('constraint', 'outline', [(0, 0), (5000, 5000)], step='floorplan', index='2')

    assert int(1000 * asic.calc_yield(chip, step='floorplan', index='0')) == 245
    assert int(1000 * asic.calc_yield(chip, step='floorplan', index='1')) == 495
    assert int(1000 * asic.calc_yield(chip, step='floorplan', index='2')) == 996


@pytest.mark.nostrict
def test_calc_yield_murphy():
    chip = siliconcompiler.Chip('test')
    chip.load_target(freepdk45_demo)

    chip.set('constraint', 'outline', [(0, 0), (150000, 75000)])
    # Rounding to int(1000x) to avoid noise in float
    assert int(1000 * asic.calc_yield(chip, model='murphy')) == 288

    chip.set('constraint', 'outline', [(0, 0), (75000, 75000)])
    assert int(1000 * asic.calc_yield(chip, model='murphy')) == 515

    chip.set('constraint', 'outline', [(0, 0), (5000, 5000)])
    assert int(1000 * asic.calc_yield(chip, model='murphy')) == 996


def test_calc_yield_murphy_with_stepindex():
    chip = siliconcompiler.Chip('test')
    chip.load_target(freepdk45_demo)

    chip.set('constraint', 'outline', [(0, 0), (150000, 75000)], step='floorplan', index='0')
    chip.set('constraint', 'outline', [(0, 0), (75000, 75000)], step='floorplan', index='1')
    chip.set('constraint', 'outline', [(0, 0), (5000, 5000)], step='floorplan', index='2')

    # Rounding to int(1000x) to avoid noise in float
    assert int(1000 * asic.calc_yield(chip, step='floorplan', index='0', model='murphy')) == 288
    assert int(1000 * asic.calc_yield(chip, step='floorplan', index='1', model='murphy')) == 515
    assert int(1000 * asic.calc_yield(chip, step='floorplan', index='2', model='murphy')) == 996


#########################
if __name__ == "__main__":
    test_calc_dpw()
