# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler

def test_summary(datadir):

    chip = siliconcompiler.Chip()
    manifest = os.path.join(datadir, 'gcd.pkg.json')

    chip.read_manifest(manifest)

    chip.summary()


#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_summary(datadir(__file__))
