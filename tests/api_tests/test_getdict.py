# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_getdict():

    chip = siliconcompiler.Chip()
    chip.target('freepdk45')
    localcfg = chip.getdict('pdk')

    assert localcfg['process']['value'] == 'freepdk45'

#########################
if __name__ == "__main__":
    test_getdict()
