# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import pytest

@pytest.mark.nostrict
def test_calc_area():

    chip = siliconcompiler.Chip('test')

    # Test rectangle
    chip.set('constraint', 'outline', [(0,0), (10,10)])
    assert chip.calc_area() == 100.0

    # Test rectilinear shape
    chip.set('constraint', 'outline', [(0,0), (0,20), (10,20), (10,10), (20,10), (20,0)])
    assert chip.calc_area() == 300.0

def test_calc_area_with_stepindex():
    chip = siliconcompiler.Chip('test')

    # Test rectangle
    chip.set('constraint', 'outline', [(0,0), (10,10)], step='floorplan', index='0')

    # Test rectilinear shape
    chip.set('constraint', 'outline', [(0,0), (0,20), (10,20), (10,10), (20,10), (20,0)], step='floorplan', index='1')

    assert chip.calc_area(step='floorplan', index='0') == 100.0
    assert chip.calc_area(step='floorplan', index='1') == 300.0

@pytest.mark.nostrict
def test_calc_dpw():

    chip = siliconcompiler.Chip('test')
    chip.load_target('skywater130_demo')

    chip.set('constraint', 'outline', [(0,0), (150000, 75000)])
    assert chip.calc_dpw() == 0

    chip.set('constraint', 'outline', [(0,0), (75000, 75000)])
    assert chip.calc_dpw() == 4

    chip.set('constraint', 'outline', [(0,0), (5000, 5000)])
    assert chip.calc_dpw() == 2520

def test_calc_dpw_with_stepindex():

    chip = siliconcompiler.Chip('test')
    chip.load_target('skywater130_demo')

    chip.set('constraint', 'outline', [(0,0), (150000, 75000)], step='floorplan', index='0')
    chip.set('constraint', 'outline', [(0,0), (75000, 75000)], step='floorplan', index='1')
    chip.set('constraint', 'outline', [(0,0), (5000, 5000)], step='floorplan', index='2')

    assert chip.calc_dpw(step='floorplan', index='0') == 0
    assert chip.calc_dpw(step='floorplan', index='1') == 4
    assert chip.calc_dpw(step='floorplan', index='2') == 2520

@pytest.mark.nostrict
def test_calc_yield_poisson():
    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    chip.set('constraint', 'outline', [(0,0), (150000, 75000)])
    assert int(1000 * chip.calc_yield()) == 245

    chip.set('constraint', 'outline', [(0,0), (75000, 75000)])
    assert int(1000 * chip.calc_yield()) == 495

    chip.set('constraint', 'outline', [(0,0), (5000, 5000)])
    assert int(1000 * chip.calc_yield()) == 996

def test_calc_yield_poisson_with_stepindex():
    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    chip.set('constraint', 'outline', [(0,0), (150000, 75000)], step='floorplan', index='0')
    chip.set('constraint', 'outline', [(0,0), (75000, 75000)], step='floorplan', index='1')
    chip.set('constraint', 'outline', [(0,0), (5000, 5000)], step='floorplan', index='2')

    assert int(1000 * chip.calc_yield(step='floorplan', index='0')) == 245
    assert int(1000 * chip.calc_yield(step='floorplan', index='1')) == 495
    assert int(1000 * chip.calc_yield(step='floorplan', index='2')) == 996

@pytest.mark.nostrict
def test_calc_yield_murphy():
    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    chip.set('constraint', 'outline', [(0,0), (150000, 75000)])
    # Rounding to int(1000x) to avoid noise in float
    assert int(1000 * chip.calc_yield(model='murphy')) == 288

    chip.set('constraint', 'outline', [(0,0), (75000, 75000)])
    assert int(1000 * chip.calc_yield(model='murphy')) == 515

    chip.set('constraint', 'outline', [(0,0), (5000, 5000)])
    assert int(1000 * chip.calc_yield(model='murphy')) == 996

def test_calc_yield_murphy_with_stepindex():
    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    chip.set('constraint', 'outline', [(0,0), (150000, 75000)], step='floorplan', index='0')
    chip.set('constraint', 'outline', [(0,0), (75000, 75000)], step='floorplan', index='1')
    chip.set('constraint', 'outline', [(0,0), (5000, 5000)], step='floorplan', index='2')

    # Rounding to int(1000x) to avoid noise in float
    assert int(1000 * chip.calc_yield(step='floorplan', index='0', model='murphy')) == 288
    assert int(1000 * chip.calc_yield(step='floorplan', index='1', model='murphy')) == 515
    assert int(1000 * chip.calc_yield(step='floorplan', index='2', model='murphy')) == 996


#########################
if __name__ == "__main__":
    test_calc_dpw()
