# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler

def test_read_manifest(datadir):

    chip = siliconcompiler.Chip()
    manifest = os.path.join(datadir, 'gcd.pkg.json')
    chip.read_manifest(manifest)

def test_read_manifest_fields():
    '''Ensure that changes to fields other than 'value' are reflected by read_manifest()'''

    chip = siliconcompiler.Chip()
    chip.set('source', False, field='copy')
    chip.add('source', 'foo.v')
    chip.write_manifest('tmp.json')

    # fresh chip, so we don't retain anything from `chip` in-memory
    chip2 = siliconcompiler.Chip()
    chip2.read_manifest('tmp.json')
    assert chip2.get('source', field='copy') is False

#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_read_manifest(datadir(__file__))
