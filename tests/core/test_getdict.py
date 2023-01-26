# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
from siliconcompiler.targets import freepdk45_demo

def test_getdict():

    chip = siliconcompiler.Chip('test')
    chip.use(freepdk45_demo)
    localcfg = chip.getdict('pdk')

    assert localcfg['freepdk45']['foundry']['value'] == 'virtual'

#########################
if __name__ == "__main__":
    test_getdict()
