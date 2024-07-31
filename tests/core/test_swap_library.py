from siliconcompiler import Chip, Schema
from siliconcompiler import Library
import pytest


@pytest.mark.nostrict
def test_swap_library_sublibrary_no_main():
    chip = Chip('<test>')

    lib = Library(chip, 'main_lib')
    sub_lib = Library(chip, 'sub_lib', auto_enable=True)
    lib.use(sub_lib)

    chip.use(lib)

    assert chip.get('option', 'library') == []
    assert chip.get('library', 'main_lib', 'option', 'library') == ['sub_lib']

    chip.swap_library('sub_lib', 'new_lib')

    assert chip.get('option', 'library') == []
    assert chip.get('library', 'main_lib', 'option', 'library') == ['new_lib']


def test_swap_library_sublibrary_no_main_stepindex():
    chip = Chip('<test>')

    lib = Library(chip, 'main_lib')
    sub_lib = Library(chip, 'sub_lib', auto_enable=True)
    lib.use(sub_lib)

    chip.use(lib)

    assert chip.get('option', 'library',
                    step=Schema.GLOBAL_KEY, index=Schema.GLOBAL_KEY) == []
    assert chip.get('library', 'main_lib', 'option', 'library',
                    step=Schema.GLOBAL_KEY, index=Schema.GLOBAL_KEY) == ['sub_lib']

    chip.swap_library('sub_lib', 'new_lib', step='import', index='4')

    assert chip.get('option', 'library',
                    step=Schema.GLOBAL_KEY, index=Schema.GLOBAL_KEY) == []
    assert chip.get('library', 'main_lib', 'option', 'library',
                    step=Schema.GLOBAL_KEY, index=Schema.GLOBAL_KEY) == ['sub_lib']
    assert chip.get('library', 'main_lib', 'option', 'library',
                    step='import', index=Schema.GLOBAL_KEY) == ['sub_lib']
    assert chip.get('library', 'main_lib', 'option', 'library',
                    step='import', index='4') == ['new_lib']


@pytest.mark.nostrict
def test_auto_enable_sublibrary_with_main():
    chip = Chip('<test>')

    lib = Library(chip, 'main_lib', auto_enable=True)
    sub_lib = Library(chip, 'sub_lib', auto_enable=True)
    lib.use(sub_lib)

    chip.use(lib)

    assert chip.get('option', 'library') == ['main_lib']
    assert chip.get('library', 'main_lib', 'option', 'library') == ['sub_lib']

    chip.swap_library('main_lib', 'new_lib')

    assert chip.get('option', 'library') == ['new_lib']
    assert chip.get('library', 'main_lib', 'option', 'library') == ['sub_lib']
