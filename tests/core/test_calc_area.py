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

#########################
if __name__ == "__main__":
    test_calc_area()
