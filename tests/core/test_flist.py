import os
import pathlib
import pytest

from siliconcompiler import Chip


@pytest.mark.nostrict
def test_import_flist_rel_paths(datadir):
    chip = Chip('dummy')
    chip.import_flist(os.path.join(datadir, 'flist', 'files.flist'))

    assert "flist-files.flist" in chip.getkeys('package', 'source')

    assert chip.get('input', 'rtl', 'verilog') == ["dummy.v"]
    assert chip.get('input', 'rtl', 'verilog', field='package') == ['flist-files.flist']
    assert None not in chip.find_files('input', 'rtl', 'verilog')

    assert chip.get('option', 'idir') == ["."]
    assert chip.get('option', 'idir', field='package') == ['flist-files.flist']

    assert chip.get('option', 'define') == ["TEST=1"]


@pytest.mark.nostrict
def test_import_flist_abs_paths():
    chip = Chip('dummy')

    dummy_path = os.path.abspath('dummy.v')
    with open(dummy_path, 'w') as f:
        f.write("// test\n")

    os.makedirs("flist", exist_ok=True)
    os.makedirs("incs", exist_ok=True)

    with open('flist/flist', 'w') as f:
        f.write("// test\n")
        f.write(dummy_path + "\n")
        f.write("+incdir+" + os.path.abspath("incs") + "\n")

    chip.import_flist('flist/flist')

    assert "flist-flist" in chip.getkeys('package', 'source')

    assert chip.get('input', 'rtl', 'verilog') == [
        pathlib.PureWindowsPath(os.path.abspath("dummy.v")).as_posix()]
    assert chip.get('input', 'rtl', 'verilog', field='package') == [None]
    assert None not in chip.find_files('input', 'rtl', 'verilog')

    assert chip.get('option', 'idir') == [
        pathlib.PureWindowsPath(os.path.abspath("incs")).as_posix()]
    assert chip.get('option', 'idir', field='package') == [None]


@pytest.mark.nostrict
def test_import_flist_abs_package_paths():
    chip = Chip('dummy')

    dummy_path = os.path.abspath('dummy.v')
    with open(dummy_path, 'w') as f:
        f.write("// test\n")

    os.makedirs("incs", exist_ok=True)

    with open('flist', 'w') as f:
        f.write("// test\n")
        f.write(dummy_path + "\n")
        f.write("+incdir+" + os.path.abspath("incs") + "\n")

    chip.import_flist('flist')

    assert "flist-flist" in chip.getkeys('package', 'source')

    assert chip.get('input', 'rtl', 'verilog') == ["dummy.v"]
    assert chip.get('input', 'rtl', 'verilog', field='package') == ['flist-flist']
    assert None not in chip.find_files('input', 'rtl', 'verilog')

    assert chip.get('option', 'idir') == ["incs"]
    assert chip.get('option', 'idir', field='package') == ['flist-flist']


@pytest.mark.nostrict
def test_import_flist_env_paths():
    chip = Chip('dummy')

    dummy_path = os.path.abspath('dummy.v')
    with open(dummy_path, 'w') as f:
        f.write("// test\n")

    with open('flist', 'w') as f:
        f.write("// test\n")
        f.write("${SRC_PATH}/dummy.v\n")

    chip.set('option', 'env', 'SRC_PATH', os.path.dirname(dummy_path))
    chip.import_flist('flist')

    assert "flist-flist" in chip.getkeys('package', 'source')

    assert chip.get('input', 'rtl', 'verilog') == ["dummy.v"]
    assert chip.get('input', 'rtl', 'verilog', field='package') == ['flist-flist']
    assert None not in chip.find_files('input', 'rtl', 'verilog')


@pytest.mark.nostrict
def test_import_flist_package(datadir):
    chip = Chip('dummy')

    chip.register_source('dummy_source', datadir)

    chip.import_flist('flist/files.flist', package='dummy_source')

    assert "flist-files.flist" in chip.getkeys('package', 'source')

    assert chip.get('input', 'rtl', 'verilog') == ["dummy.v"]
    assert chip.get('input', 'rtl', 'verilog', field='package') == ['flist-files.flist']
    assert None not in chip.find_files('input', 'rtl', 'verilog')

    assert chip.get('option', 'idir') == ["."]
    assert chip.get('option', 'idir', field='package') == ['flist-files.flist']

    assert chip.get('option', 'define') == ["TEST=1"]
