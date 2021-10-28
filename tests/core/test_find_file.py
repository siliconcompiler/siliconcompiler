# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler

def test_find_sc_file():

    chip = siliconcompiler.Chip()

    assert chip._find_sc_file("flows/asicflow.py") is not None
    assert chip._find_sc_file("pdks/freepdk45.py") is not None

    datadir = os.path.dirname(os.path.abspath(__file__)) + "/../data/"
    chip.set('scpath', f'{datadir}/sclib')
    assert chip._find_sc_file('test.txt') is not None

    assert chip._find_sc_file('my_file_that_doesnt_exist.blah', missing_ok=True) is None
    assert chip.error == 0

    assert chip._find_sc_file('my_file_that_doesnt_exist.blah') is None
    assert chip.error == 1

#########################
if __name__ == "__main__":
    test_find_sc_file()
