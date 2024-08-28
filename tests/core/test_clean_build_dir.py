import os
from siliconcompiler import Chip
from siliconcompiler.targets import freepdk45_demo
from siliconcompiler.scheduler import _setup_workdir, clean_build_dir
from siliconcompiler import NodeStatus
from siliconcompiler.flowgraph import nodes_to_execute
from siliconcompiler.tools.builtin import nop


def test_clean_build_dir():
    chip = Chip('test')
    chip.use(freepdk45_demo)
    chip.set('option', 'clean', True)

    # Create folders
    for step, index in nodes_to_execute(chip):
        _setup_workdir(chip, step, index, False)

    clean_build_dir(chip)

    for step, index in nodes_to_execute(chip):
        assert not os.path.exists(chip.getworkdir(step=step, index=index)), f'({step}, {index})'
    assert not os.path.exists(chip.getworkdir())


def test_clean_build_dir_from():
    chip = Chip('test')
    chip.use(freepdk45_demo)

    # Create folders
    for step, index in nodes_to_execute(chip):
        _setup_workdir(chip, step, index, False)

    chip.set('option', 'from', 'place')

    clean_build_dir(chip)

    for step, index in nodes_to_execute(chip):
        assert not os.path.exists(chip.getworkdir(step=step, index=index)), f'({step}, {index})'

    assert os.path.exists(chip.getworkdir(step='import_verilog', index='0'))
    assert os.path.exists(chip.getworkdir(step='import_vhdl', index='0'))
    assert os.path.exists(chip.getworkdir(step='syn', index='0'))
    assert os.path.exists(chip.getworkdir(step='floorplan', index='0'))
    assert os.path.exists(chip.getworkdir())


def test_clean_build_dir_clean():
    chip = Chip('test')
    chip.use(freepdk45_demo)

    # Create folders
    for step, index in nodes_to_execute(chip):
        _setup_workdir(chip, step, index, False)
        chip.set('record', 'status', NodeStatus.SUCCESS, step=step, index=index)
        cfg = f"{chip.getworkdir(step=step, index=index)}/outputs/{chip.design}.pkg.json"
        chip.write_manifest(cfg)

    clean_build_dir(chip)

    for step, index in nodes_to_execute(chip):
        assert os.path.exists(chip.getworkdir(step=step, index=index)), f'({step}, {index})'
    assert os.path.exists(chip.getworkdir())


def test_clean_build_dir_in_run():
    chip = Chip('test')
    chip.use(freepdk45_demo)

    # Create folders
    for step, index in nodes_to_execute(chip):
        _setup_workdir(chip, step, index, False)

    chip.set('arg', 'step', 'blah')

    clean_build_dir(chip)

    for step, index in nodes_to_execute(chip):
        assert os.path.exists(chip.getworkdir(step=step, index=index)), f'({step}, {index})'
    assert os.path.exists(chip.getworkdir())


def test_clean_build_dir_in_remote():
    chip = Chip('test')
    chip.use(freepdk45_demo)

    # Create folders
    for step, index in nodes_to_execute(chip):
        _setup_workdir(chip, step, index, False)

    chip.set('record', 'remoteid', 'blah')

    clean_build_dir(chip)

    for step, index in nodes_to_execute(chip):
        assert os.path.exists(chip.getworkdir(step=step, index=index)), f'({step}, {index})'
    assert os.path.exists(chip.getworkdir())


def test_clean_build_dir_change_flow():
    chip = Chip('test')
    chip.use(freepdk45_demo)

    chip.node('test0', 'step', nop)
    chip.set('option', 'flow', 'test0')

    chip.node('test1', 'step_new', nop)

    chip.run()

    assert os.path.exists(chip.getworkdir(step='step', index='0'))
    manifest = os.path.join(chip.getworkdir(), f'{chip.design}.pkg.json')
    assert os.path.exists(manifest)
    old_manifest_time = os.path.getmtime(manifest)

    chip.set('option', 'flow', 'test1')

    chip.run()

    # make sure old folders are gone
    assert not os.path.exists(chip.getworkdir(step='step', index='0'))
    assert os.path.exists(chip.getworkdir(step='step_new', index='0'))
    manifest = os.path.join(chip.getworkdir(), f'{chip.design}.pkg.json')
    new_manifest_time = os.path.getmtime(manifest)

    assert old_manifest_time != new_manifest_time


def test_clean_build_dir_change_flow_same_name():
    chip = Chip('test')
    chip.use(freepdk45_demo)

    chip.node('test0', 'step', nop)
    chip.set('option', 'flow', 'test0')

    chip.node('test1', 'step', nop)

    chip.run()

    assert os.path.exists(chip.getworkdir(step='step', index='0'))
    assert os.path.exists(os.path.join(chip.getworkdir(), f'{chip.design}.pkg.json'))
    old_step_time = os.path.getmtime(chip.getworkdir(step='step', index='0'))

    chip.set('option', 'flow', 'test1')

    chip.run()

    assert os.path.exists(chip.getworkdir(step='step', index='0'))
    assert os.path.exists(os.path.join(chip.getworkdir(), f'{chip.design}.pkg.json'))
    new_step_time = os.path.getmtime(chip.getworkdir(step='step', index='0'))

    # new flow, so it should have rerun
    assert old_step_time != new_step_time


def test_clean_build_dir_change_flow_with_collect():
    chip = Chip('test')
    chip.use(freepdk45_demo)

    os.makedirs('ydir', exist_ok=True)
    chip.add('option', 'ydir', 'ydir')
    chip.set('option', 'ydir', True, field='copy')

    chip.node('test0', 'step', nop)
    chip.set('option', 'flow', 'test0')

    chip.node('test1', 'step', nop)

    chip.run()

    assert os.path.exists(chip.getworkdir(step='step', index='0'))
    assert os.path.exists(os.path.join(chip.getworkdir(), f'{chip.design}.pkg.json'))
    old_step_time = os.path.getmtime(chip.getworkdir(step='step', index='0'))

    chip.set('option', 'flow', 'test0')
    chip.collect()

    chip.run()

    assert os.path.exists(chip.getworkdir(step='step', index='0'))
    assert os.path.exists(os.path.join(chip.getworkdir(), f'{chip.design}.pkg.json'))
    new_step_time = os.path.getmtime(chip.getworkdir(step='step', index='0'))

    # should not have been rerun
    assert old_step_time == new_step_time
