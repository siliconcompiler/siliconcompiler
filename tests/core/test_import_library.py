from siliconcompiler import Chip
from siliconcompiler import Library, PDK
from siliconcompiler.tools._common import get_libraries
import pytest


@pytest.mark.nostrict
def test_auto_enable_sublibrary_no_main():
    chip = Chip('<test>')

    lib = Library('main_lib')
    sub_lib = Library('sub_lib', auto_enable=True)
    lib.use(sub_lib)

    chip.use(lib)

    assert chip.get('option', 'library') == []
    assert get_libraries(chip) == set()


@pytest.mark.nostrict
def test_auto_enable_sublibrary_with_main():
    chip = Chip('<test>')

    lib = Library('main_lib', auto_enable=True)
    sub_lib = Library('sub_lib', auto_enable=True)
    lib.use(sub_lib)

    chip.use(lib)

    assert chip.get('option', 'library') == ['main_lib']
    assert get_libraries(chip) == set(['main_lib', 'sub_lib'])


@pytest.mark.nostrict
def test_auto_enable():
    chip = Chip('<test>')

    lib = Library('main_lib', auto_enable=True)
    chip.use(lib)

    assert chip.get('option', 'library') == ['main_lib']
    assert get_libraries(chip) == set(['main_lib'])


def test_recursive_import_lib_only():
    chip = Chip('<test>')

    lib = Library('main_lib')
    sub_lib = Library('sub_lib')
    lib.use(sub_lib)

    chip.use(lib)

    assert 'sub_lib' in chip.getkeys('library')
    assert 'main_lib' in chip.getkeys('library')
    assert 'library' not in chip.getkeys('library', 'main_lib')


def test_recursive_import_with_package_source():
    chip = Chip('<test>')

    lib = Library('main_lib')
    sub_lib = Library('sub_lib')
    sub_lib.register_source('test', 'test_path', 'test_ref')
    lib.use(sub_lib)

    chip.use(lib)

    assert 'sub_lib' in chip.getkeys('library')
    assert chip.get('package', 'source', 'test', 'path') == 'test_path'
    assert chip.get('package', 'source', 'test', 'ref') == 'test_ref'


def test_import_pdk_with_data_source():
    chip = Chip('<test>')

    pdk = PDK('main_pdk')
    pdk.register_source('test', 'test_path', 'test_ref')

    chip.use(pdk)

    assert 'main_pdk' in chip.getkeys('pdk')
    assert chip.get('package', 'source', 'test', 'path') == 'test_path'
    assert chip.get('package', 'source', 'test', 'ref') == 'test_ref'


def test_import_library_as_chip():
    chip = Chip('<test>')

    lib = Chip('<lib>')
    assert 'pdk' in lib.getkeys()
    assert 'history' in lib.getkeys()
    assert 'library' in lib.getkeys()
    assert 'input' in lib.getkeys()
    assert 'output' in lib.getkeys()
    assert 'option' in lib.getkeys()
    assert 'asic' in lib.getkeys()
    assert 'package' in lib.getkeys()

    chip.use(lib)
    assert 'pdk' not in chip.getkeys('library', '<lib>')
    assert 'history' not in chip.getkeys('library', '<lib>')
    assert 'library' not in chip.getkeys('library', '<lib>')
    assert 'input' not in chip.getkeys('library', '<lib>')
    assert 'output' in chip.getkeys('library', '<lib>')
    assert 'option' in chip.getkeys('library', '<lib>')
    assert 'asic' in chip.getkeys('library', '<lib>')
    assert 'package' in chip.getkeys('library', '<lib>')

    assert 'pdk' in lib.getkeys()
    assert 'history' in lib.getkeys()
    assert 'library' in lib.getkeys()
    assert 'input' in lib.getkeys()
    assert 'output' in lib.getkeys()
    assert 'option' in lib.getkeys()
    assert 'asic' in lib.getkeys()
    assert 'package' in lib.getkeys()


def test_import_library_as_library():
    chip = Chip('<test>')

    lib = Library('<lib>')
    assert 'pdk' in lib.getkeys()
    assert 'history' in lib.getkeys()
    assert 'library' in lib.getkeys()
    assert 'input' in lib.getkeys()
    assert 'output' in lib.getkeys()
    assert 'option' in lib.getkeys()
    assert 'asic' in lib.getkeys()
    assert 'package' in lib.getkeys()

    chip.use(lib)
    assert 'pdk' not in chip.getkeys('library', '<lib>')
    assert 'history' not in chip.getkeys('library', '<lib>')
    assert 'library' not in chip.getkeys('library', '<lib>')
    assert 'input' in chip.getkeys('library', '<lib>')
    assert 'output' in chip.getkeys('library', '<lib>')
    assert 'option' in chip.getkeys('library', '<lib>')
    assert 'asic' in chip.getkeys('library', '<lib>')
    assert 'package' in chip.getkeys('library', '<lib>')

    assert 'pdk' in lib.getkeys()
    assert 'history' in lib.getkeys()
    assert 'library' in lib.getkeys()
    assert 'input' in lib.getkeys()
    assert 'output' in lib.getkeys()
    assert 'option' in lib.getkeys()
    assert 'asic' in lib.getkeys()
    assert 'package' in lib.getkeys()
