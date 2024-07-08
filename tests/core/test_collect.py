import siliconcompiler
from siliconcompiler.targets import asic_demo
import os
import pytest
from siliconcompiler.scheduler import _setup_node


@pytest.mark.nostrict
def test_collect_file_update():
    # Checks if collected files are properly updated after editing

    # Create instance of Chip class
    with open('fake.v', 'w') as f:
        f.write('fake')
    chip = siliconcompiler.Chip('fake')
    chip.input('fake.v')
    chip.collect()
    filename = chip.find_files('input', 'rtl', 'verilog')[0]

    with open(os.path.join(chip._getcollectdir(), filename), 'r') as f:
        assert f.readline() == 'fake'

    # Edit file
    with open('fake.v', 'w') as f:
        f.write('newfake')

    # Rerun remote run
    chip.collect()
    with open(os.path.join(chip._getcollectdir(), filename), 'r') as f:
        assert f.readline() == 'newfake'


def test_collect_file_asic_demo():
    chip = siliconcompiler.Chip('demo')
    chip.load_target(asic_demo)
    chip.collect()

    for f in chip.find_files('input', 'rtl', 'verilog', step='import', index=0):
        assert f.startswith(chip._getcollectdir())


def test_collect_file_verbose():
    chip = siliconcompiler.Chip('demo')
    chip.load_target(asic_demo)
    chip._add_file_logger('log')
    chip.collect()

    with open('log') as f:
        text = f.read()
        assert "Collecting input sources" in text
        assert "Copying " in text


def test_collect_file_not_verbose():
    chip = siliconcompiler.Chip('demo')
    chip.load_target(asic_demo)
    chip._add_file_logger('log')
    chip.collect(verbose=False)

    with open('log') as f:
        text = f.read()
        assert "Collecting input sources" not in text
        assert "Copying " not in text


def test_collect_file_copyall():
    chip = siliconcompiler.Chip('demo')
    chip.load_target(asic_demo)
    chip.set('option', 'copyall', True)
    chip.collect()

    # check that all file are copied (input, library, and pdk)
    assert len(os.listdir(chip._getcollectdir())) == 42


def test_collect_file_copyall_with_tools():
    chip = siliconcompiler.Chip('demo')
    chip.load_target(asic_demo)
    chip.set('option', 'copyall', True)

    _setup_node(chip, 'syn', '0')
    _setup_node(chip, 'floorplan', '0')

    chip.collect()

    # check that all file are copied (input, library, and pdk)
    assert len(os.listdir(chip._getcollectdir())) == 48


def test_collect_file_copyall_with_dir():
    chip = siliconcompiler.Chip('demo')
    chip.load_target(asic_demo)
    chip.set('option', 'copyall', True)

    os.mkdir('testdir')

    _setup_node(chip, 'syn', '0')
    _setup_node(chip, 'floorplan', '0')
    chip.set('tool', 'openroad', 'path', 'testdir')

    chip.collect()

    # check that all file are copied (input, library, and pdk)
    assert len(os.listdir(chip._getcollectdir())) == 49


def test_collect_file_copyall_with_false():
    chip = siliconcompiler.Chip('demo')
    chip.load_target(asic_demo)
    chip.set('input', 'rtl', 'verilog', False, field='copy')
    chip.set('option', 'copyall', True)
    chip.collect()

    # check that all file are copied (input, library, and pdk)
    assert len(os.listdir(chip._getcollectdir())) == 42


def test_collect_file_with_false():
    chip = siliconcompiler.Chip('demo')
    chip.load_target(asic_demo)
    chip.set('input', 'rtl', 'verilog', False, field='copy')
    chip.collect()

    # No files should have been collected
    assert len(os.listdir(chip._getcollectdir())) == 0
