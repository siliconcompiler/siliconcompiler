import os
from siliconcompiler import Chip
from siliconcompiler.targets import freepdk45_demo
from siliconcompiler.scheduler import _setup_workdir


def test_clean_build_dir():
    chip = Chip('test')
    chip.load_target(freepdk45_demo)

    # Create folders
    for step, index in chip.nodes_to_execute():
        _setup_workdir(chip, step, index, False)

    chip.clean_build_dir()

    for step, index in chip.nodes_to_execute():
        assert not os.path.exists(chip._getworkdir(step=step, index=index)), f'({step}, {index})'
    assert not os.path.exists(chip._getworkdir())


def test_clean_build_dir_from():
    chip = Chip('test')
    chip.load_target(freepdk45_demo)

    # Create folders
    for step, index in chip.nodes_to_execute():
        _setup_workdir(chip, step, index, False)

    chip.set('option', 'from', 'place')

    chip.clean_build_dir()

    for step, index in chip.nodes_to_execute():
        assert not os.path.exists(chip._getworkdir(step=step, index=index)), f'({step}, {index})'

    assert os.path.exists(chip._getworkdir(step='import', index='0'))
    assert os.path.exists(chip._getworkdir(step='syn', index='0'))
    assert os.path.exists(chip._getworkdir(step='floorplan', index='0'))
    assert os.path.exists(chip._getworkdir())


def test_clean_build_dir_resume():
    chip = Chip('test')
    chip.load_target(freepdk45_demo)

    # Create folders
    for step, index in chip.nodes_to_execute():
        _setup_workdir(chip, step, index, False)

    chip.set('option', 'resume', True)

    chip.clean_build_dir()

    for step, index in chip.nodes_to_execute():
        assert os.path.exists(chip._getworkdir(step=step, index=index)), f'({step}, {index})'
    assert os.path.exists(chip._getworkdir())


def test_clean_build_dir_in_run():
    chip = Chip('test')
    chip.load_target(freepdk45_demo)

    # Create folders
    for step, index in chip.nodes_to_execute():
        _setup_workdir(chip, step, index, False)

    chip.set('arg', 'step', 'blah')

    chip.clean_build_dir()

    for step, index in chip.nodes_to_execute():
        assert os.path.exists(chip._getworkdir(step=step, index=index)), f'({step}, {index})'
    assert os.path.exists(chip._getworkdir())


def test_clean_build_dir_in_remote():
    chip = Chip('test')
    chip.load_target(freepdk45_demo)

    # Create folders
    for step, index in chip.nodes_to_execute():
        _setup_workdir(chip, step, index, False)

    chip.set('record', 'remoteid', 'blah')

    chip.clean_build_dir()

    for step, index in chip.nodes_to_execute():
        assert os.path.exists(chip._getworkdir(step=step, index=index)), f'({step}, {index})'
    assert os.path.exists(chip._getworkdir())
