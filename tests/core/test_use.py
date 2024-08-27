import pytest
from siliconcompiler import Chip, Library


def test_module_input():
    chip = Chip('test')

    lib = Library(chip, 'testlib')
    chip.use(lib)

    assert 'testlib' in chip.getkeys('library')


def test_function_input():
    chip = Chip('test')

    def func(chip):
        return Library(chip, 'testlib')
    chip.use(func)

    assert 'testlib' in chip.getkeys('library')


def test_none_input():
    chip = Chip('test')

    with pytest.raises(ValueError):
        chip.use(None)


def test_function_spec():
    chip = Chip('test')

    def func(chip, other):
        pass

    with pytest.raises(RuntimeError):
        chip.use(func)


def test_chip_passing():
    chip = Chip('test')

    def func(chip):
        assert isinstance(chip, Chip)

    chip.use(func)


def test_chip_not_passing():
    chip = Chip('test')

    def func():
        raise EnvironmentError

    with pytest.raises(EnvironmentError):
        chip.use(func)
