# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import os
import siliconcompiler

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_find():

    chip = siliconcompiler.Chip()
    chip.set('scpath', 'examples/sclib')
    error = 0
    if not chip.find("flows/asicflow.py"):
        error = 1
    if not chip.find("foundries/freepdk45.py"):
        error = 1

    assert not error

#########################
if __name__ == "__main__":
    test_find()
