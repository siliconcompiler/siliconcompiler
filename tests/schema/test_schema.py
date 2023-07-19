import pathlib

import pytest

from siliconcompiler.schema import Schema
from siliconcompiler.schema.schema_cfg import scparam


def test_list_of_lists():
    cfg = {}
    scparam(cfg, ['test'], sctype='[[str]]', shorthelp='Test')

    schema = Schema(cfg=cfg)
    schema.set('test', [['foo']])

    assert schema.get('test') == [['foo']]


def test_list_of_bools():
    cfg = {}
    scparam(cfg, ['test'], sctype='[bool]', shorthelp='Test')

    schema = Schema(cfg=cfg)
    schema.set('test', [True, False])

    assert schema.get('test') == [True, False]


def test_pernode_mandatory():
    cfg = {}
    scparam(cfg, ['test'], sctype='str', shorthelp='Test', pernode='required')

    schema = Schema(cfg=cfg)

    # Should fail
    with pytest.raises(ValueError):
        schema.set('test', 'foo')

    # Should succeed
    assert schema.set('test', 'foo', step='syn', index=0)


def test_empty():
    schema = Schema()
    assert schema._is_empty('package', 'version')

    schema.set('package', 'version', '1.0')
    assert not schema._is_empty('package', 'version')


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
