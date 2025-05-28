import os
from siliconcompiler import Chip
from siliconcompiler.targets import freepdk45_demo
from siliconcompiler.scheduler import clean_build_dir
from siliconcompiler import NodeStatus
from siliconcompiler.tools.builtin import nop
from siliconcompiler.flowgraph import RuntimeFlowgraph
from siliconcompiler.tool import ToolSchema


def test_clean_build_dir():
    chip = Chip('test')
    chip.use(freepdk45_demo)
    chip.set('option', 'clean', True)

    runtime = RuntimeFlowgraph(
        chip.schema.get("flowgraph", chip.get('option', 'flow'), field='schema'),
        from_steps=chip.get('option', 'from'),
        to_steps=chip.get('option', 'to'),
        prune_nodes=chip.get('option', 'prune'))

    # Create folders
    for step, index in runtime.get_nodes():
        ToolSchema().setup_work_directory(
            chip.getworkdir(step=step, index=index), remove_exist=False)

    clean_build_dir(chip)

    for step, index in runtime.get_nodes():
        assert not os.path.exists(chip.getworkdir(step=step, index=index)), f'({step}, {index})'
    assert not os.path.exists(chip.getworkdir())


def test_clean_build_dir_from():
    chip = Chip('test')
    chip.use(freepdk45_demo)

    runtime = RuntimeFlowgraph(
        chip.schema.get("flowgraph", chip.get('option', 'flow'), field='schema'),
        from_steps=chip.get('option', 'from'),
        to_steps=chip.get('option', 'to'),
        prune_nodes=chip.get('option', 'prune'))

    # Create folders
    for step, index in runtime.get_nodes():
        ToolSchema().setup_work_directory(
            chip.getworkdir(step=step, index=index), remove_exist=False)

    chip.set('option', 'from', 'place.global')

    clean_build_dir(chip)

    runtime = RuntimeFlowgraph(
        chip.schema.get("flowgraph", chip.get('option', 'flow'), field='schema'),
        from_steps=chip.get('option', 'from'),
        to_steps=chip.get('option', 'to'),
        prune_nodes=chip.get('option', 'prune'))

    for step, index in runtime.get_nodes():
        assert not os.path.exists(chip.getworkdir(step=step, index=index)), f'({step}, {index})'

    assert os.path.exists(chip.getworkdir(step='import.verilog', index='0'))
    assert os.path.exists(chip.getworkdir(step='import.vhdl', index='0'))
    assert os.path.exists(chip.getworkdir(step='syn', index='0'))
    assert os.path.exists(chip.getworkdir(step='floorplan.init', index='0'))
    assert os.path.exists(chip.getworkdir(step='floorplan.pin_placement', index='0'))
    assert os.path.exists(chip.getworkdir())


def test_clean_build_dir_clean():
    chip = Chip('test')
    chip.use(freepdk45_demo)

    runtime = RuntimeFlowgraph(
        chip.schema.get("flowgraph", chip.get('option', 'flow'), field='schema'),
        from_steps=chip.get('option', 'from'),
        to_steps=chip.get('option', 'to'),
        prune_nodes=chip.get('option', 'prune'))

    # Create folders
    for step, index in runtime.get_nodes():
        ToolSchema().setup_work_directory(
            chip.getworkdir(step=step, index=index), remove_exist=False)

        chip.set('record', 'status', NodeStatus.SUCCESS, step=step, index=index)
        cfg = f"{chip.getworkdir(step=step, index=index)}/outputs/{chip.design}.pkg.json"
        chip.write_manifest(cfg)

    clean_build_dir(chip)

    for step, index in runtime.get_nodes():
        assert os.path.exists(chip.getworkdir(step=step, index=index)), f'({step}, {index})'
    assert os.path.exists(chip.getworkdir())


def test_clean_build_dir_in_run():
    chip = Chip('test')
    chip.use(freepdk45_demo)

    runtime = RuntimeFlowgraph(
        chip.schema.get("flowgraph", chip.get('option', 'flow'), field='schema'),
        from_steps=chip.get('option', 'from'),
        to_steps=chip.get('option', 'to'),
        prune_nodes=chip.get('option', 'prune'))

    # Create folders
    for step, index in runtime.get_nodes():
        ToolSchema().setup_work_directory(
            chip.getworkdir(step=step, index=index), remove_exist=False)

    chip.set('arg', 'step', 'floorplan.init')

    clean_build_dir(chip)

    for step, index in runtime.get_nodes():
        assert os.path.exists(chip.getworkdir(step=step, index=index)), f'({step}, {index})'
    assert os.path.exists(chip.getworkdir())


def test_clean_build_dir_in_remote():
    chip = Chip('test')
    chip.use(freepdk45_demo)

    runtime = RuntimeFlowgraph(
        chip.schema.get("flowgraph", chip.get('option', 'flow'), field='schema'),
        from_steps=chip.get('option', 'from'),
        to_steps=chip.get('option', 'to'),
        prune_nodes=chip.get('option', 'prune'))

    # Create folders
    for step, index in runtime.get_nodes():
        ToolSchema().setup_work_directory(
            chip.getworkdir(step=step, index=index), remove_exist=False)

    chip.set('record', 'remoteid', 'blah')

    clean_build_dir(chip)

    for step, index in runtime.get_nodes():
        assert os.path.exists(chip.getworkdir(step=step, index=index)), f'({step}, {index})'
    assert os.path.exists(chip.getworkdir())


def test_clean_build_dir_change_flow():
    chip = Chip('test')
    chip.use(freepdk45_demo)

    chip.node('test0', 'step', nop)
    chip.set('option', 'flow', 'test0')

    chip.node('test1', 'step_new', nop)

    assert chip.run()

    assert os.path.exists(chip.getworkdir(step='step', index='0'))
    manifest = os.path.join(chip.getworkdir(), f'{chip.design}.pkg.json')
    assert os.path.exists(manifest)
    old_manifest_time = os.path.getmtime(manifest)

    chip.set('option', 'flow', 'test1')

    assert chip.run()

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

    assert chip.run()

    assert os.path.exists(chip.getworkdir(step='step', index='0'))
    assert os.path.exists(os.path.join(chip.getworkdir(), f'{chip.design}.pkg.json'))
    old_step_time = os.path.getmtime(chip.getworkdir(step='step', index='0'))

    chip.set('option', 'flow', 'test1')

    assert chip.run()

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

    assert chip.run()

    assert os.path.exists(chip.getworkdir(step='step', index='0'))
    assert os.path.exists(os.path.join(chip.getworkdir(), f'{chip.design}.pkg.json'))
    old_step_time = os.path.getmtime(chip.getworkdir(step='step', index='0'))

    chip.set('option', 'flow', 'test0')
    chip.collect()

    assert chip.run()

    assert os.path.exists(chip.getworkdir(step='step', index='0'))
    assert os.path.exists(os.path.join(chip.getworkdir(), f'{chip.design}.pkg.json'))
    new_step_time = os.path.getmtime(chip.getworkdir(step='step', index='0'))

    # should not have been rerun
    assert old_step_time == new_step_time
