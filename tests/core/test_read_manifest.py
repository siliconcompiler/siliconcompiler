# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler
import copy
import json
from siliconcompiler import _metadata

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

def test_read_defaults(datadir):
    '''Make sure read/write operaton doesn't modify manifest'''

    DEBUG = False

    # gets defaul from schema
    chip = siliconcompiler.Chip()

    # check that read/write doesn't modify
    chip.write_manifest("actual.json", prune=False)
    chip.read_manifest("actual.json")

    # independent dump of chip.cfg
    with open("actual.json", 'w') as f:
        print(json.dumps(chip.cfg, indent=4, sort_keys=True), file=f)
    with open("actual.json", 'r') as f:
        actual = json.load(f)

    # expected
    with open(os.path.join(datadir, 'defaults.json'), 'r') as f:
        expected = json.load(f)

    # special case (initialized in constructor)
    expected['version']['software']['defvalue'] = _metadata.version
    expected['version']['software']['value'] = _metadata.version

    assert actual == expected

#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_read_defaults(datadir(__file__))
