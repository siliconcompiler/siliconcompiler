# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler

def test_summary(datadir):

    chip = siliconcompiler.Chip()
    manifest = os.path.join(datadir, 'gcd.pkg.json')

    chip.read_manifest(manifest)

    chip.summary()

def test_steplist(datadir, capfd):
    with capfd.disabled():
        chip = siliconcompiler.Chip()
        manifest = os.path.join(datadir, 'gcd.pkg.json')

        chip.read_manifest(manifest)
        chip.set('steplist', ['syn'])

    chip.summary()
    stdout, _ = capfd.readouterr()

    assert 'import0' not in stdout
    assert 'syn0' in stdout

#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_summary(datadir(__file__))
