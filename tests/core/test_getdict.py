# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

def test_getdict():

    chip = siliconcompiler.Chip()
    chip.load_target('freepdk45_demo')
    localcfg = chip.getdict('pdk')

    assert localcfg['process']['value'] == 'freepdk45'

#########################
if __name__ == "__main__":
    test_getdict()
