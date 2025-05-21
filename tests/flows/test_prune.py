import siliconcompiler

from siliconcompiler.tools.builtin import nop, minimum, maximum
from core.tools.dummy import runner
from siliconcompiler._common import SiliconCompilerError
from siliconcompiler.targets import freepdk45_demo

import pytest
import time


def test_prune_end(caplogger):
    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)
    log = caplogger(chip)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.node(flow, 'syn', nop)
    chip.edge(flow, 'import', 'syn')
    chip.set('option', 'prune', ('syn', '0'))

    with pytest.raises(SiliconCompilerError,
                       match=f"{flow} flowgraph contains errors and cannot be run."):
        chip.run(raise_exception=True)

    assert "pruning removed all exit nodes for syn in the test flowgraph" in log()


def test_prune_middle(caplogger):
    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)
    log = caplogger(chip)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.node(flow, 'syn', nop)
    chip.node(flow, 'place', nop)
    chip.edge(flow, 'import', 'syn')
    chip.edge(flow, 'syn', 'place')
    chip.set('option', 'prune', ('syn', '0'))

    with pytest.raises(SiliconCompilerError,
                       match="test flowgraph contains errors and cannot be run"):
        chip.run(raise_exception=True)

    assert "no path from import0 to place0 in the test flowgraph" in log()


def test_prune_split():
    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.node(flow, 'syn', nop, index=0)
    chip.node(flow, 'syn', nop, index=1)
    chip.node(flow, 'place', nop, index=0)
    chip.node(flow, 'place', nop, index=1)
    chip.edge(flow, 'import', 'syn', head_index=0)
    chip.edge(flow, 'import', 'syn', head_index=1)
    chip.edge(flow, 'syn', 'place', head_index=0, tail_index=0)
    chip.edge(flow, 'syn', 'place', head_index=1, tail_index=1)
    chip.set('option', 'prune', ('syn', '0'))

    assert chip.run()


def test_prune_split_join(caplogger):
    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)
    log = caplogger(chip)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.node(flow, 'syn', nop, index=0)
    chip.node(flow, 'syn', nop, index=1)
    chip.node(flow, 'place', runner)
    chip.edge(flow, 'import', 'syn', head_index=0)
    chip.edge(flow, 'import', 'syn', head_index=1)
    chip.edge(flow, 'syn', 'place', tail_index=0)
    chip.edge(flow, 'syn', 'place', tail_index=1)
    # Remove all syn
    chip.set('option', 'prune', [('syn', '0'), ('syn', '1')])

    with pytest.raises(SiliconCompilerError,
                       match="test flowgraph contains errors and cannot be run."):
        chip.run(raise_exception=True)

    assert "no path from import0 to place0 in the test flowgraph" in log()


def test_prune_split_disc3235():
    # https://github.com/siliconcompiler/siliconcompiler/discussions/3235#discussion-7994517
    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'compile', nop)
    chip.node(flow, 'elaborate', nop)
    chip.node(flow, 'sim1', nop)
    chip.node(flow, 'sim2', nop)
    chip.node(flow, 'sim3', nop)
    chip.node(flow, 'sim4', nop)
    chip.node(flow, 'merge', nop)
    chip.node(flow, 'report', nop)

    chip.edge(flow, 'compile', 'elaborate')
    chip.edge(flow, 'elaborate', 'sim1')
    chip.edge(flow, 'elaborate', 'sim2')
    chip.edge(flow, 'elaborate', 'sim3')
    chip.edge(flow, 'elaborate', 'sim4')
    chip.edge(flow, 'sim1', 'merge')
    chip.edge(flow, 'sim2', 'merge')
    chip.edge(flow, 'sim3', 'merge')
    chip.edge(flow, 'sim4', 'merge')
    chip.edge(flow, 'merge', 'report')
    chip.set('option', 'prune', [('sim1', '0'), ('sim3', '0')])

    assert chip.run()

    assert chip.get('record', 'status', step='sim1', index='0') == "pending"
    assert chip.get('record', 'status', step='sim2', index='0') == "success"
    assert chip.get('record', 'status', step='sim3', index='0') == "pending"
    assert chip.get('record', 'status', step='sim4', index='0') == "success"
    assert chip.get('record', 'status', step='merge', index='0') == "success"
    assert chip.get('record', 'status', step='report', index='0') == "success"


def test_input_provides_with_prune_multirun():
    chip = siliconcompiler.Chip('test')
    flow_name = 'test_flow'

    flow = siliconcompiler.Flow(flow_name)
    flow.node(flow_name, 'initial', nop)
    flow.node(flow_name, 'onestep', nop)
    flow.node(flow_name, 'twostep', nop)
    flow.node(flow_name, 'finalstep', nop)
    flow.edge(flow_name, 'initial', 'onestep')
    flow.edge(flow_name, 'initial', 'twostep')
    flow.edge(flow_name, 'onestep', 'finalstep')
    flow.edge(flow_name, 'twostep', 'finalstep')

    chip.use(flow)
    chip.set('option', 'flow', flow_name)
    chip.set('tool', 'builtin', 'task', 'nop', 'output', 'test.txt', step='initial', index='0')
    chip.set('tool', 'builtin', 'task', 'nop', 'output', 'test.txt', step='onestep', index='0')
    chip.set('tool', 'builtin', 'task', 'nop', 'output', 'test.txt', step='twostep', index='0')

    chip.set('option', 'prune', ('onestep', '0'))
    assert chip.run()
    assert chip.get('record', 'status', step='finalstep', index='0') == "success"
    assert chip.get('record', 'inputnode', step='finalstep', index='0') == [('twostep', '0')]
    end_time = chip.get('record', 'endtime', step='finalstep', index='0')

    # Add delay to ensure end time is different
    time.sleep(2)

    chip.set('option', 'prune', ('twostep', '0'))
    assert chip.run(raise_exception=True)
    assert chip.get('record', 'status', step='finalstep', index='0') == "success"
    assert chip.get('record', 'inputnode', step='finalstep', index='0') == [('onestep', '0')]
    assert chip.get('record', 'endtime', step='finalstep', index='0') != end_time
    end_time = chip.get('record', 'endtime', step='finalstep', index='0')

    # Add delay to ensure end time is different
    time.sleep(2)

    chip.unset('option', 'prune')
    assert chip.run()
    assert chip.get('record', 'status', step='finalstep', index='0') == "success"
    assert set(chip.get('record', 'inputnode', step='finalstep', index='0')) == \
        set([('onestep', '0'), ('twostep', '0')])
    assert chip.get('record', 'endtime', step='finalstep', index='0') != end_time


def test_input_provides_with_prune_multirun_default_select_inputs(monkeypatch):
    # Remove use of builtin's _select_inputs to test the default _select_inputs
    monkeypatch.delattr(nop, '_select_inputs')

    chip = siliconcompiler.Chip('test')
    flow_name = 'test_flow'

    flow = siliconcompiler.Flow(flow_name)
    flow.node(flow_name, 'initial', nop)
    flow.node(flow_name, 'onestep', nop)
    flow.node(flow_name, 'twostep', nop)
    flow.node(flow_name, 'finalstep', nop)
    flow.edge(flow_name, 'initial', 'onestep')
    flow.edge(flow_name, 'initial', 'twostep')
    flow.edge(flow_name, 'onestep', 'finalstep')
    flow.edge(flow_name, 'twostep', 'finalstep')

    chip.use(flow)
    chip.set('option', 'flow', flow_name)

    chip.set('option', 'prune', ('onestep', '0'))
    assert chip.run()
    assert chip.get('record', 'status', step='finalstep', index='0') == "success"
    assert chip.get('record', 'inputnode', step='finalstep', index='0') == [('twostep', '0')]
    end_time = chip.get('record', 'endtime', step='finalstep', index='0')

    # Add delay to ensure end time is different
    time.sleep(2)

    chip.set('option', 'prune', ('twostep', '0'))
    assert chip.run()
    assert chip.get('record', 'status', step='finalstep', index='0') == "success"
    assert chip.get('record', 'inputnode', step='finalstep', index='0') == [('onestep', '0')]
    assert chip.get('record', 'endtime', step='finalstep', index='0') != end_time
    end_time = chip.get('record', 'endtime', step='finalstep', index='0')

    # Add delay to ensure end time is different
    time.sleep(2)

    chip.unset('option', 'prune')
    assert chip.run()
    assert chip.get('record', 'status', step='finalstep', index='0') == "success"
    assert set(chip.get('record', 'inputnode', step='finalstep', index='0')) == \
        set([('onestep', '0'), ('twostep', '0')])
    assert chip.get('record', 'endtime', step='finalstep', index='0') != end_time


def test_input_provides_with_prune_multirun_with_min():
    chip = siliconcompiler.Chip('test')
    flow_name = 'test_flow'

    flow = siliconcompiler.Flow(flow_name)
    flow.node(flow_name, 'initial', nop)
    flow.node(flow_name, 'onestep', nop)
    flow.node(flow_name, 'twostep', nop)
    flow.node(flow_name, 'finalstep', minimum)
    flow.edge(flow_name, 'initial', 'onestep')
    flow.edge(flow_name, 'initial', 'twostep')
    flow.edge(flow_name, 'onestep', 'finalstep')
    flow.edge(flow_name, 'twostep', 'finalstep')

    chip.use(flow)
    chip.set('option', 'flow', flow_name)
    chip.set('tool', 'builtin', 'task', 'nop', 'output', 'test.txt', step='initial', index='0')
    chip.set('tool', 'builtin', 'task', 'nop', 'output', 'test.txt', step='onestep', index='0')
    chip.set('tool', 'builtin', 'task', 'nop', 'output', 'test.txt', step='twostep', index='0')

    chip.set('option', 'prune', ('onestep', '0'))
    assert chip.run()
    assert chip.get('record', 'status', step='finalstep', index='0') == "success"
    end_time = chip.get('record', 'endtime', step='finalstep', index='0')

    # Add delay to ensure end time is different
    time.sleep(2)

    chip.set('option', 'prune', ('twostep', '0'))
    assert chip.run()
    assert chip.get('record', 'status', step='finalstep', index='0') == "success"
    assert chip.get('record', 'endtime', step='finalstep', index='0') != end_time
    end_time = chip.get('record', 'endtime', step='finalstep', index='0')

    # Add delay to ensure end time is different
    time.sleep(2)

    chip.unset('option', 'prune')
    assert chip.run()
    assert chip.get('record', 'status', step='finalstep', index='0') == "success"
    assert chip.get('record', 'endtime', step='finalstep', index='0') != end_time


def test_prune_nodenotpresent(caplogger):
    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)
    log = caplogger(chip)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'compile', nop)
    chip.node(flow, 'elaborate', nop)
    chip.node(flow, 'sim1', nop, index=0)
    chip.node(flow, 'sim1', nop, index=1)
    chip.node(flow, 'sim3', nop)
    chip.node(flow, 'sim4', nop)
    chip.node(flow, 'merge', nop)
    chip.node(flow, 'report', nop)

    chip.edge(flow, 'compile', 'elaborate')
    chip.edge(flow, 'elaborate', 'sim1', head_index=0)
    chip.edge(flow, 'elaborate', 'sim1', head_index=1)
    chip.edge(flow, 'elaborate', 'sim3')
    chip.edge(flow, 'elaborate', 'sim4')
    chip.edge(flow, 'sim1', 'merge', tail_index=0)
    chip.edge(flow, 'sim1', 'merge', tail_index=1)
    chip.edge(flow, 'sim3', 'merge')
    chip.edge(flow, 'sim4', 'merge')
    chip.edge(flow, 'merge', 'report')
    chip.set('option', 'prune', [('sim1', '3')])

    with pytest.raises(SiliconCompilerError,
                       match="test flowgraph contains errors and cannot be run."):
        chip.run(raise_exception=True)

    assert "sim13 is not defined in the test flowgraph" in log()


def test_prune_min():
    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.node(flow, 'syn', nop, index=0)
    chip.node(flow, 'syn', nop, index=1)
    chip.node(flow, 'place', minimum)
    chip.edge(flow, 'import', 'syn', head_index=0)
    chip.edge(flow, 'import', 'syn', head_index=1)
    chip.edge(flow, 'syn', 'place', tail_index=0)
    chip.edge(flow, 'syn', 'place', tail_index=1)
    chip.set('option', 'prune', ('syn', '0'))

    assert chip.run(raise_exception=True)


def test_prune_max():
    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.node(flow, 'syn', nop, index=0)
    chip.node(flow, 'syn', nop, index=1)
    chip.node(flow, 'place', maximum)
    chip.edge(flow, 'import', 'syn', head_index=0)
    chip.edge(flow, 'import', 'syn', head_index=1)
    chip.edge(flow, 'syn', 'place', tail_index=0)
    chip.edge(flow, 'syn', 'place', tail_index=1)
    chip.set('option', 'prune', ('syn', '0'))

    assert chip.run()


def test_prune_max_all_inputs_pruned(caplogger):
    chip = siliconcompiler.Chip('foo')
    chip.use(freepdk45_demo)
    log = caplogger(chip)

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.node(flow, 'syn', nop, index=0)
    chip.node(flow, 'syn', nop, index=1)
    chip.node(flow, 'place', maximum)
    chip.edge(flow, 'import', 'syn', head_index=0)
    chip.edge(flow, 'import', 'syn', head_index=1)
    chip.edge(flow, 'syn', 'place', tail_index=0)
    chip.edge(flow, 'syn', 'place', tail_index=1)
    chip.set('option', 'prune', [('syn', '0'), ('syn', '1')])

    with pytest.raises(SiliconCompilerError,
                       match="test flowgraph contains errors and cannot be run."):
        chip.run(raise_exception=True)

    assert "no path from import0 to place0 in the test flowgraph" in log()
