# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler
import json
import packaging.version

import pytest


def test_read_manifest_fields():
    '''Ensure that changes to fields other than 'value' are reflected by read_manifest()'''

    chip = siliconcompiler.Chip('foo')
    chip.set('input', 'rtl', 'verilog', False, field='copy')
    chip.input('foo.v')
    chip.write_manifest('tmp.json')

    # fresh chip, so we don't retain anything from `chip` in-memory
    chip2 = siliconcompiler.Chip('foo')
    chip2.read_manifest('tmp.json')
    assert chip2.get('input', 'rtl', 'verilog', field='copy') is False


def test_read_sup():
    '''Test compressed read/write'''

    chip = siliconcompiler.Chip('foo')
    chip.input('foo.v')
    chip.write_manifest('tmp.sup.gz')

    chip2 = siliconcompiler.Chip('foo')
    chip2.read_manifest('tmp.sup.gz')
    assert chip2.get('input', 'rtl', 'verilog', step='import', index=0) == ['foo.v']


# Use nostrict mark to prevent changing default value of [option, strict]
@pytest.mark.nostrict
def test_modified_schema(datadir):
    '''Make sure schema has not been modified without updating defaults.json'''

    # gets default from schema
    chip = siliconcompiler.Chip('test')

    # expected
    with open(os.path.join(datadir, 'defaults.json'), 'r') as f:
        expected = json.load(f)

    # special case (initialized in constructor)
    glbl_key = siliconcompiler.Schema.GLOBAL_KEY
    expected['design']['node'][glbl_key] = {}
    expected['design']['node'][glbl_key][glbl_key] = {
        'value': 'test',
        'signature': None
    }

    assert chip.schema.cfg == expected


# Use nostrict mark to prevent changing default value of [option, strict]
@pytest.mark.nostrict
def test_last_schema(datadir):
    chip = siliconcompiler.Chip('test')
    current_version = packaging.version.Version(chip.get('schemaversion'))
    # Attempt to read in last version of schema
    chip.read_manifest(os.path.join(datadir, 'last_major.json'))

    last_version = packaging.version.Version(chip.get('schemaversion'))

    # ensure the versions match
    assert current_version.major == last_version.major
    assert current_version.minor == last_version.minor
    assert last_version.micro == 0


def test_read_history():
    '''Make sure that history gets included in manifest read.'''
    chip = siliconcompiler.Chip('foo')
    chip.input('foo.v')
    chip.schema.record_history()
    chip.write_manifest('tmp.json')

    chip2 = siliconcompiler.Chip('foo')
    chip2.read_manifest('tmp.json')
    assert chip.get('input', 'rtl', 'verilog', job='job0', step='import', index=0) == ['foo.v']


def test_read_job():
    '''Make sure that we can read a manifest into a non-default job'''
    chip = siliconcompiler.Chip('foo')
    chip.input('foo.v')
    chip.write_manifest('tmp.json')

    chip2 = siliconcompiler.Chip('foo')
    chip2.read_manifest('tmp.json', job='job1')
    assert chip2.get('input', 'rtl', 'verilog', job='job1', step='import', index=0) == ['foo.v']


#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_modified_schema(datadir(__file__))
    test_read_sup()
