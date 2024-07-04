# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import pytest

import siliconcompiler


@pytest.fixture
def chip():
    return siliconcompiler.Chip('top')


def test_basic_setget(chip):
    design = chip.get('design')
    assert design == "top"


def test_list_access(chip):
    # Check list access
    inlist = ['import', 'syn']
    chip.set('option', 'from', inlist)
    assert inlist == chip.get('option', 'from')


def test_scalar_to_list_access(chip):
    inscalar = 'import'
    chip.set('option', 'from', 'import')
    outlist = chip.get('option', 'from')
    assert outlist == [inscalar]


def test_illegal_key(chip):
    # check illegal key (expected error)
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        chip.set('badquery', 'top')


def test_error_scalar_add(chip):
    # check error on scalar add
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        chip.add('design', 'top')


def test_error_assign_list(chip):
    # check assigning list to scalar
    with pytest.raises(siliconcompiler.core.SiliconCompilerError):
        chip.set('design', ['top'])


@pytest.mark.parametrize('src_type,src_value,dst_type,dst_value', [
    ('int', 3, 'str', '3'),
    ('float', 3.5, 'str', '3.5'),
    ('str', '3', 'str', '3'),
    ('bool', True, 'str', 'true'),
    ('int', 3, 'int', 3),
    ('float', 3.5, 'int', 3),
    ('str', '3', 'int', 3),
    ('bool', True, 'int', 1),
    ('int', 3, 'float', 3),
    ('float', 3.5, 'float', 3.5),
    ('str', '3', 'float', 3),
    ('bool', True, 'float', 1),
    ('int', 0, 'bool', False),
    ('float', 1.0, 'bool', True),
    ('str', 'true', 'bool', True),
    ('bool', True, 'bool', True)])
def test_change_type_singlular_to_singlular(src_type, src_value, dst_type, dst_value):
    chip = siliconcompiler.Chip('test')

    chip.schema.change_type('option', 'var', 'test', type=src_type)
    assert chip.get('option', 'var', 'test', field='type') == src_type

    chip.set('option', 'var', 'test', src_value)
    assert chip.get('option', 'var', 'test') == src_value

    chip.schema.change_type('option', 'var', 'test', type=dst_type)
    assert chip.get('option', 'var', 'test', field='type') == dst_type
    assert chip.get('option', 'var', 'test') == dst_value


@pytest.mark.parametrize('src_type,src_value,dst_type,dst_value', [
    ('int', 3, '[str]', ['3']),
    ('float', 3.5, '[str]', ['3.5']),
    ('str', '3', '[str]', ['3']),
    ('bool', True, '[str]', ['true']),
    ('int', 3, '[int]', [3]),
    ('float', 3.5, '[int]', [3]),
    ('str', '3', '[int]', [3]),
    ('bool', True, '[int]', [1]),
    ('int', 3, '[float]', [3]),
    ('float', 3.5, '[float]', [3.5]),
    ('str', '3', '[float]', [3]),
    ('bool', True, '[float]', [1]),
    ('int', 0, '[bool]', [False]),
    ('float', 1.0, '[bool]', [True]),
    ('str', 'true', '[bool]', [True]),
    ('bool', True, '[bool]', [True])])
def test_change_type_singlular_to_list(src_type, src_value, dst_type, dst_value):
    chip = siliconcompiler.Chip('test')

    chip.schema.change_type('option', 'var', 'test', type=src_type)
    assert chip.get('option', 'var', 'test', field='type') == src_type

    chip.set('option', 'var', 'test', src_value)
    assert chip.get('option', 'var', 'test') == src_value

    chip.schema.change_type('option', 'var', 'test', type=dst_type)
    assert chip.get('option', 'var', 'test', field='type') == dst_type
    assert chip.get('option', 'var', 'test') == dst_value


@pytest.mark.parametrize('src_type,src_value,dst_type,dst_value', [
    ('[int]', [3, 4], '[str]', ['3', '4']),
    ('[float]', [3.5, 5], '[str]', ['3.5', '5.0']),
    ('[str]', ['3'], '[str]', ['3']),
    ('[bool]', [False, True], '[str]', ['false', 'true']),
    ('[int]', [3], '[int]', [3]),
    ('[float]', [3.5], '[int]', [3]),
    ('[str]', ['3'], '[int]', [3]),
    ('[bool]', [True], '[int]', [1]),
    ('[int]', [3], '[float]', [3]),
    ('[float]', [3.5], '[float]', [3.5]),
    ('[str]', ['3', '3.5'], '[float]', [3, 3.5]),
    ('[bool]', [False, True], '[float]', [0, 1]),
    ('[int]', [0], '[bool]', [False]),
    ('[float]', [1.0], '[bool]', [True]),
    ('[str]', ['false', 'true'], '[bool]', [False, True]),
    ('[bool]', [True], '[bool]', [True])])
def test_change_type_list_to_list(src_type, src_value, dst_type, dst_value):
    chip = siliconcompiler.Chip('test')

    chip.schema.change_type('option', 'var', 'test', type=src_type)
    assert chip.get('option', 'var', 'test', field='type') == src_type

    chip.set('option', 'var', 'test', src_value)
    assert chip.get('option', 'var', 'test') == src_value

    chip.schema.change_type('option', 'var', 'test', type=dst_type)
    assert chip.get('option', 'var', 'test', field='type') == dst_type
    assert chip.get('option', 'var', 'test') == dst_value


@pytest.mark.parametrize('src_type,src_value,dst_type,dst_value', [
    ('[int]', [3], 'str', '3'),
    ('[float]', [3.5], 'str', '3.5'),
    ('[str]', ['3'], 'str', '3'),
    ('[bool]', [False], 'str', 'false'),
    ('[int]', [3], 'int', 3),
    ('[float]', [3.5], 'int', 3),
    ('[str]', ['3'], 'int', 3),
    ('[bool]', [True], 'int', 1),
    ('[int]', [3], 'float', 3),
    ('[float]', [3.5], 'float', 3.5),
    ('[str]', ['3'], 'float', 3),
    ('[bool]', [False], 'float', 0),
    ('[int]', [0], 'bool', False),
    ('[float]', [1.0], 'bool', True),
    ('[str]', ['false'], 'bool', False),
    ('[bool]', [True], 'bool', True)])
def test_change_type_list_to_sinular(src_type, src_value, dst_type, dst_value):
    chip = siliconcompiler.Chip('test')

    chip.schema.change_type('option', 'var', 'test', type=src_type)
    assert chip.get('option', 'var', 'test', field='type') == src_type

    chip.set('option', 'var', 'test', src_value)
    assert chip.get('option', 'var', 'test') == src_value

    chip.schema.change_type('option', 'var', 'test', type=dst_type)
    assert chip.get('option', 'var', 'test', field='type') == dst_type
    assert chip.get('option', 'var', 'test') == dst_value


def test_change_type_list_to_sinular_error():
    chip = siliconcompiler.Chip('test')

    chip.schema.change_type('option', 'var', 'test', type='[str]')

    chip.set('option', 'var', 'test', ['test1', 'test2'])
    assert chip.get('option', 'var', 'test') == ['test1', 'test2']

    with pytest.raises(ValueError):
        chip.schema.change_type('option', 'var', 'test', type='str')
