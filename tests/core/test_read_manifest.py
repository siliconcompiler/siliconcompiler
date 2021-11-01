# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler

def test_read_manifest(datadir):

    chip = siliconcompiler.Chip()
    manifest = os.path.join(datadir, 'gcd.pkg.json')
    chip.read_manifest(manifest)

#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_read_manifest(datadir(__file__))
