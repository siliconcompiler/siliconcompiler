# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import os

def test_calc_area():

    chip = siliconcompiler.Chip()

    # Test rectangle
    chip.set('asic','diearea', [(0,0), (10,10)])
    area = chip.calc_area()
    assert (area == 100.0)

    # Test rectilinear shape
    chip.set('asic','diearea', [(0,0), (0,20), (10,20), (10,10), (20,10), (20,0)])
    area = chip.calc_area()
    assert (area == 300.0)

#########################
if __name__ == "__main__":
    test_calc_area()
