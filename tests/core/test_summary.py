# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
from siliconcompiler import NodeStatus

import pytest

from siliconcompiler.tools.openroad import place
from siliconcompiler.tools.openroad import cts

from siliconcompiler.tools.builtin import nop
from siliconcompiler.tools.builtin import minimum

from siliconcompiler.flowgraph import _get_flowgraph_node_inputs, nodes_to_execute


@pytest.fixture
def gcd_with_metrics(gcd_chip):
    steps = nodes_to_execute(gcd_chip)

    dummy_data = 0
    flow = gcd_chip.get('option', 'flow')
    for step in gcd_chip.getkeys('flowgraph', flow):
        dummy_data += 1
        for index in gcd_chip.getkeys('flowgraph', flow, step):
            for metric in gcd_chip.getkeys('flowgraph', flow, step, index, 'weight'):
                gcd_chip.set('flowgraph', flow, step, index, 'status', NodeStatus.SUCCESS)
                gcd_chip.set('metric', metric, str(dummy_data), step=step, index=index)
                for input in _get_flowgraph_node_inputs(gcd_chip, flow, (step, index)):
                    if input in steps:
                        gcd_chip.set('flowgraph', flow, step, index, 'select', input)

    return gcd_chip


def test_summary(gcd_with_metrics):
    gcd_with_metrics.summary()


def test_from_to(gcd_with_metrics, capfd):
    with capfd.disabled():
        gcd_with_metrics.set('option', 'from', ['syn'])
        gcd_with_metrics.set('option', 'to', ['syn'])

    gcd_with_metrics.summary()
    stdout, _ = capfd.readouterr()
    # Summary output is hidden by capfd, so we print it to aid in debugging
    print(stdout)

    assert 'import0' in stdout
    assert 'syn0' in stdout
    assert 'floorplan' not in stdout


def test_parallel_path(capfd):
    with capfd.disabled():
        chip = siliconcompiler.Chip('test')

        flow = 'test'
        chip.set('option', 'flow', flow)
        chip.node(flow, 'import', nop)
        chip.node(flow, 'ctsmin', minimum)

        chip.set('flowgraph', flow, 'import', '0', 'status', siliconcompiler.NodeStatus.SUCCESS)
        chip.set('flowgraph', flow, 'ctsmin', '0', 'status', siliconcompiler.NodeStatus.SUCCESS)
        chip.set('flowgraph', flow, 'ctsmin', '0', 'select', ('cts', '1'))

        for i in ('0', '1', '2'):
            chip.node(flow, 'place', place, index=i)
            chip.node(flow, 'cts', cts, index=i)

            chip.set('flowgraph', flow, 'place', i, 'status', siliconcompiler.NodeStatus.SUCCESS)
            chip.set('flowgraph', flow, 'cts', i, 'status', siliconcompiler.NodeStatus.SUCCESS)

            chip.edge(flow, 'place', 'cts', tail_index=i, head_index=i)
            chip.edge(flow, 'cts', 'ctsmin', tail_index=i)
            chip.edge(flow, 'import', 'place', head_index=i)

            chip.set('flowgraph', flow, 'place', i, 'select', ('import', '0'))
            chip.set('flowgraph', flow, 'cts', i, 'select', ('place', i))

            chip.set('metric', 'errors', 0, step='place', index=i)
            chip.set('metric', 'errors', 0, step='cts', index=i)

    chip.write_flowgraph('test_graph.png')

    chip.summary()
    stdout, _ = capfd.readouterr()
    # Summary output is hidden by capfd, so we print it to aid in debugging
    print(stdout)
    assert 'place1' in stdout
    assert 'cts1' in stdout
    assert 'place0' not in stdout
    assert 'cts0' not in stdout
    assert 'place2' not in stdout
    assert 'cts2' not in stdout
