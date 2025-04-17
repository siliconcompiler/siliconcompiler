import pathlib
import os

import pytest

from siliconcompiler.schema import Schema
from siliconcompiler.schema.utils import PerNode
from siliconcompiler.schema.schema_cfg import scparam
from siliconcompiler import Chip
from siliconcompiler.targets import asic_demo


def test_add_keypath_error():
    schema = Schema()
    with pytest.raises(ValueError):
        schema.add('input', 'verilog', 'foo.v')


def test_pathlib():
    schema = Schema()

    file_path = pathlib.Path('path/to/file.txt')
    schema.set('option', 'file', 'test', file_path)
    assert schema.get('option', 'file', 'test') == [str(file_path)]

    dir_path = pathlib.Path('a/directory/')
    schema.set('option', 'dir', 'test', dir_path)
    assert schema.get('option', 'dir', 'test') == [str(dir_path)]


def test_allkeys():
    schema = Schema()

    assert len(schema.allkeys()) > 0

    partial = schema.allkeys('option')

    assert len(partial) > 0
    assert sorted(partial)[0] == ('breakpoint',)

    complete = schema.allkeys('option', 'breakpoint')
    assert complete == []


def test_merge_with_init_old_has_values():
    old_schema = Schema().cfg

    scparam(old_schema, ['test'], sctype='[[str]]', shorthelp='Test')

    new_schema = Schema(cfg=old_schema)
    assert new_schema.getdict('test')

    new_schema._merge_with_init_schema()

    with pytest.raises(ValueError):
        new_schema.getdict('test')


def test_merge_with_init_new_has_values():
    old_schema = Schema().cfg

    del old_schema['package']

    new_schema = Schema(cfg=old_schema)
    with pytest.raises(ValueError):
        new_schema.getdict('package')

    new_schema._merge_with_init_schema()

    assert new_schema.getdict('package')


def test_merge_with_init_with_lib():
    chip = Chip('')
    chip.use(asic_demo)

    chip.schema._merge_with_init_schema()

    assert 'sky130hd' in chip.getkeys('library')


def test_copy_key_param():
    schema = Schema()

    schema.set('option', 'pdk', 'test')
    schema.set('option', 'pdk', 'test', field='help')

    assert schema.get('option', 'stackup', field='help') != 'test'

    schema.copy_key(src=('option', 'pdk'), dst=('option', 'stackup'))

    assert schema.get('option', 'stackup') == 'test'
    assert schema.get('option', 'stackup', field='help') == 'test'


def test_copy_key_file():
    chip = Chip('')

    os.makedirs("testingdir")
    chip.register_source('test', os.path.abspath("testingdir"))
    with open('testingdir/test.v', 'w') as f:
        f.write('test')

    file_path = os.path.join(os.path.abspath("testingdir"), "test.v")
    chip.set('option', 'file', 'test', 'test.v', package='test')
    assert chip.find_files('option', 'file', 'test') == [file_path]

    assert 'test1' not in chip.getkeys('option', 'file')
    chip.schema.copy_key(src=('option', 'file', 'test'), dst=('option', 'file', 'test1'))
    assert chip.find_files('option', 'file', 'test1') == [file_path]
