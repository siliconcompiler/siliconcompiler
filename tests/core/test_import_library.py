from siliconcompiler import Chip
from siliconcompiler import Library


def test_recursive_import_lib_only():
    chip = Chip('<test>')

    lib = Library(chip, 'main_lib')
    sub_lib = Library(chip, 'sub_lib')
    lib.use(sub_lib)

    chip.use(lib)

    assert 'sub_lib' in chip.getkeys('library')
    assert 'library' not in chip.getkeys('library', 'main_lib')


def test_recursive_import_with_package_source():
    chip = Chip('<test>')

    lib = Library(chip, 'main_lib')
    sub_lib = Library(chip, 'sub_lib')
    sub_lib.register_package_source('test', 'test_path', 'test_ref')
    lib.use(sub_lib)

    chip.use(lib)

    assert 'sub_lib' in chip.getkeys('library')
    assert chip.get('package', 'source', 'test', 'path') == 'test_path'
    assert chip.get('package', 'source', 'test', 'ref') == 'test_ref'
