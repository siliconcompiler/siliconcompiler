# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler
import json
import packaging.version

from siliconcompiler import Schema

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

    assert json.loads(json.dumps(schema.getdict())) == expected, "Golden manifest does not match"


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


# # Use nostrict mark to prevent changing default value of [option, strict]
@pytest.mark.nostrict
def test_last_schema_reverse(monkeypatch, datadir):
    current_schema = siliconcompiler.Schema()
    current_schema.write_manifest('current.json')

    last_schema = os.path.join(datadir, 'last_minor.json')

    def schema_cfg(schema):
        from siliconcompiler.schema import SafeSchema, EditableSchema
        safe_schema = SafeSchema.from_manifest(filepath=last_schema)
        edit_safe = EditableSchema(safe_schema)

        edit_schema = EditableSchema(schema)

        for section in safe_schema.getkeys():
            edit_schema.add(section, edit_safe.search(section))

        assert set(schema.getkeys()) == set(safe_schema.getkeys())

    monkeypatch.setattr('siliconcompiler.schema_obj.schema_cfg', schema_cfg)

    schema = siliconcompiler.Schema(logger=siliconcompiler.Chip('').logger)

    schema.read_manifest('current.json')

    current_version = packaging.version.Version(current_schema.get('schemaversion'))

    last_version = packaging.version.Version(schema.get('schemaversion'))

    # ensure the versions match
    assert current_version.major == last_version.major
    assert current_version.minor == last_version.minor
    assert current_version.micro >= last_version.micro


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
    chip2.schema.history('job1').read_manifest('tmp.json')
    assert chip2.get('input', 'rtl', 'verilog', job='job1', step='import', index=0) == ['foo.v']
