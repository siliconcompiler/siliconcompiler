import pytest

from siliconcompiler import Chip, SiliconCompilerError
from siliconcompiler.utils import register_metric


def test_no_register():
    chip = Chip('test')

    with pytest.raises(SiliconCompilerError,
                       match=r"Invalid keypath \('metric',\): set\(\) must be called on a complete keypath"):
        chip.set('metric', 'newmetric', step='test', index='0')


def test_register():
    chip = Chip('test')

    register_metric(chip, 'newmetric', 'float', 'shorthelp', 'long help')
    assert chip.get('metric', 'default', field='lock')

    chip.set('metric', 'newmetric', 10.5, step='test', index='0')
    assert chip.schema._getvals('metric', 'newmetric') == [(10.5, 'test', '0')]

    with pytest.raises(SiliconCompilerError,
                       match=r"Invalid keypath \('metric',\): set\(\) must be called on a complete keypath"):
        chip.set('metric', 'newmetric1', step='test', index='0')


def test_register_float():
    chip = Chip('test')

    register_metric(chip, 'newmetric', 'float', 'shorthelp', 'long help')

    chip.set('metric', 'newmetric', 10.5, step='test', index='0')
    assert chip.get('metric', 'newmetric', step='test', index='0') == 10.5


def test_register_int():
    chip = Chip('test')

    register_metric(chip, 'newmetric', 'int', 'shorthelp', 'long help')

    chip.set('metric', 'newmetric', 10, step='test', index='0')
    assert chip.get('metric', 'newmetric', step='test', index='0') == 10


def test_register_str():
    chip = Chip('test')

    with pytest.raises(ValueError, match='str is not a supported type'):
        register_metric(chip, 'newmetric', 'str', 'shorthelp', 'long help')


def test_register_list():
    chip = Chip('test')

    with pytest.raises(ValueError, match='list in metrics are not supported'):
        register_metric(chip, 'newmetric', '[int]', 'shorthelp', 'long help')


def test_register_noshorthelp():
    chip = Chip('test')

    with pytest.raises(ValueError, match='shorthelp must be provided'):
        register_metric(chip, 'newmetric', 'int', '', 'long help')


def test_register_nohelp():
    chip = Chip('test')

    with pytest.raises(ValueError, match='help must be provided'):
        register_metric(chip, 'newmetric', 'int', 'short help', '')


def test_register_override():
    chip = Chip('test')

    with pytest.raises(ValueError, match='fmax is already registered'):
        register_metric(chip, 'fmax', 'int', 'short help', 'long help')
