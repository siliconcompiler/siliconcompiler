# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler

def test_summary():

    chip = siliconcompiler.Chip()
    datadir = os.path.dirname(os.path.abspath(__file__)) + "/../data/"
    manifest = datadir + "gcd.pkg.json"

    chip.read_manifest(manifest)

    chip.summary()


#########################
if __name__ == "__main__":
    test_summary()
