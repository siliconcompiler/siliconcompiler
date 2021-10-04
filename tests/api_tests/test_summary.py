# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import os
import siliconcompiler

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_summary():

    chip = siliconcompiler.Chip()
    gcd_ex_dir = os.path.abspath(__file__)
    datadir = os.path.dirname(os.path.abspath(__file__)) + "/../data/"
    manifest = datadir + "gcd.pkg.json"

    chip.read_manifest(manifest)

    chip.summary()


#########################
if __name__ == "__main__":
    test_summary()
