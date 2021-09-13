# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import os
import siliconcompiler

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_find():

    chip = siliconcompiler.Chip()
    os.environ['SCDIR'] = 'siliconcompiler'
    os.environ['TOOLDIR'] = 'verilator'
    filepath = chip.find("$SUBDIR/tools/$LEAF/")

    assert (os.path.isdir(filepath))


#########################
if __name__ == "__main__":
    test_find()
