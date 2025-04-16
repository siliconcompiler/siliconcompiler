import pathlib

import pytest

from siliconcompiler import Schema


def test_add_keypath_error():
    schema = Schema()
    with pytest.raises(KeyError):
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

    assert not schema.allkeys('option', 'breakpoint')
