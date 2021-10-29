# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler

def test_find_sc_file(datadir):

    chip = siliconcompiler.Chip()

    assert chip._find_sc_file("flows/asicflow.py") is not None
    assert chip._find_sc_file("pdks/freepdk45.py") is not None

    chip.set('scpath', os.path.join(datadir, 'sclib'))
    assert chip._find_sc_file('test.txt') is not None

    assert chip._find_sc_file('my_file_that_doesnt_exist.blah', missing_ok=True) is None
    assert chip.error == 0

    assert chip._find_sc_file('my_file_that_doesnt_exist.blah') is None
    assert chip.error == 1

#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_find_sc_file(datadir(__file__))
