import os
from siliconcompiler import Chip
from siliconcompiler.targets import freepdk45_demo
from siliconcompiler.scheduler import _setup_workdir, clean_build_dir
from siliconcompiler import NodeStatus


def test_clean_build_dir():
    chip = Chip('test')
    chip.load_target(freepdk45_demo)

    # Create folders
    for step, index in chip.nodes_to_execute():
        _setup_workdir(chip, step, index, False)

    clean_build_dir(chip)

    for step, index in chip.nodes_to_execute():
        assert not os.path.exists(chip.getworkdir(step=step, index=index)), f'({step}, {index})'
    assert not os.path.exists(chip.getworkdir())


def test_clean_build_dir_from():
    chip = Chip('test')
    chip.load_target(freepdk45_demo)

    # Create folders
    for step, index in chip.nodes_to_execute():
        _setup_workdir(chip, step, index, False)

    chip.set('option', 'from', 'place')

    clean_build_dir(chip)

    for step, index in chip.nodes_to_execute():
        assert not os.path.exists(chip.getworkdir(step=step, index=index)), f'({step}, {index})'

    assert os.path.exists(chip.getworkdir(step='import', index='0'))
    assert os.path.exists(chip.getworkdir(step='syn', index='0'))
    assert os.path.exists(chip.getworkdir(step='floorplan', index='0'))
    assert os.path.exists(chip.getworkdir())


def test_clean_build_dir_resume():
    chip = Chip('test')
    chip.load_target(freepdk45_demo)

    # Create folders
    flow = chip.get('option', 'flow')
    for step, index in chip.nodes_to_execute():
        _setup_workdir(chip, step, index, False)
        chip.set('flowgraph', flow, step, index, 'status', NodeStatus.SUCCESS)
        cfg = f"{chip.getworkdir(step=step, index=index)}/outputs/{chip.design}.pkg.json"
        chip.write_manifest(cfg)

    chip.set('option', 'resume', True)

    clean_build_dir(chip)

    for step, index in chip.nodes_to_execute():
        assert os.path.exists(chip.getworkdir(step=step, index=index)), f'({step}, {index})'
    assert os.path.exists(chip.getworkdir())


def test_clean_build_dir_in_run():
    chip = Chip('test')
    chip.load_target(freepdk45_demo)

    # Create folders
    for step, index in chip.nodes_to_execute():
        _setup_workdir(chip, step, index, False)

    chip.set('arg', 'step', 'blah')

    clean_build_dir(chip)

    for step, index in chip.nodes_to_execute():
        assert os.path.exists(chip.getworkdir(step=step, index=index)), f'({step}, {index})'
    assert os.path.exists(chip.getworkdir())


def test_clean_build_dir_in_remote():
    chip = Chip('test')
    chip.load_target(freepdk45_demo)

    # Create folders
    for step, index in chip.nodes_to_execute():
        _setup_workdir(chip, step, index, False)

    chip.set('record', 'remoteid', 'blah')

    clean_build_dir(chip)

    for step, index in chip.nodes_to_execute():
        assert os.path.exists(chip.getworkdir(step=step, index=index)), f'({step}, {index})'
    assert os.path.exists(chip.getworkdir())
