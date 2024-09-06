# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler
import json
import packaging.version

from siliconcompiler.schema import Schema

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


# Use nostrict mark to prevent changing default value of [option, strict]
@pytest.mark.nostrict
def test_modified_schema(datadir):
    '''Make sure schema has not been modified without updating defaults.json'''

    # gets default from schema
    schema = siliconcompiler.Schema()

    # expected
    with open(os.path.join(datadir, 'defaults.json'), 'r') as f:
        expected = json.load(f)

    assert json.loads(json.dumps(schema.cfg)) == expected, "Golden manifest does not match"


# Use nostrict mark to prevent changing default value of [option, strict]
@pytest.mark.nostrict
def test_last_schema(datadir):
    schema = siliconcompiler.Schema()

    current_version = packaging.version.Version(schema.get('schemaversion'))
    # Check last version of schema
    last_schema = Schema(manifest=os.path.join(datadir, 'last_minor.json'))

    last_version = packaging.version.Version(last_schema.get('schemaversion'))

    # ensure the versions match
    assert current_version.major == last_version.major
    assert current_version.minor == last_version.minor
    assert last_version.micro == 0


# Use nostrict mark to prevent changing default value of [option, strict]
@pytest.mark.nostrict
def test_last_schema_reverse(monkeypatch, datadir):
    current_schema = siliconcompiler.Schema()
    with open('current.json', 'w') as f:
        current_schema.write_json(f)

    last_schema = os.path.join(datadir, 'last_minor.json')

    def _cfg_init(self):
        with open(last_schema) as f:
            cfg = json.load(f)

        return cfg

    monkeypatch.setattr('siliconcompiler.Schema._init_schema_cfg', _cfg_init)

    schema = siliconcompiler.Schema()

    schema.read_manifest('current.json')

    current_version = packaging.version.Version(current_schema.get('schemaversion'))

    last_version = packaging.version.Version(schema.get('schemaversion'))

    # ensure the versions match
    assert current_version.major == last_version.major
    assert current_version.minor == last_version.minor


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
