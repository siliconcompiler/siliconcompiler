# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_help():
    '''API test for help method
    '''

    chip = siliconcompiler.Chip(loglevel="INFO")
    allkeys = chip.getkeys()
    for key in allkeys:
        print(chip.help(*key))

#########################
if __name__ == "__main__":
    test_help()
