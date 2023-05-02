# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import pytest
import siliconcompiler


@pytest.fixture
def chip():
    # Create instance of Chip class
    chip = siliconcompiler.Chip('test')
    chip.load_target('freepdk45_demo')

    return chip


def test_metric_with_units(chip):
    chip._record_metric('floorplan', '0', 'peakpower', 1.05e6, None, source_unit='uW')
    assert chip.get('metric', 'peakpower', step='floorplan', index='0') == 1.05e3

    flow = chip.get('option', 'flow')
    tool = chip.get('flowgraph', flow, 'floorplan', '0', 'tool')
    task = chip.get('flowgraph', flow, 'floorplan', '0', 'task')
    assert chip.get('tool', tool, 'task', task, 'report', 'peakpower', step='floorplan', index='0') == []


def test_metric_without_units(chip):
    chip._record_metric('floorplan', '0', 'cells', 25, None)
    assert chip.get('metric', 'cells', step='floorplan', index='0') == 25

    flow = chip.get('option', 'flow')
    tool = chip.get('flowgraph', flow, 'floorplan', '0', 'tool')
    task = chip.get('flowgraph', flow, 'floorplan', '0', 'task')
    assert chip.get('tool', tool, 'task', task, 'report', 'cells', step='floorplan', index='0') == []


def test_metric_with_source(chip):
    chip._record_metric('floorplan', '0', 'cells', 25, 'report.txt')
    assert chip.get('metric', 'cells', step='floorplan', index='0') == 25

    flow = chip.get('option', 'flow')
    tool = chip.get('flowgraph', flow, 'floorplan', '0', 'tool')
    task = chip.get('flowgraph', flow, 'floorplan', '0', 'task')
    assert chip.get('tool', tool, 'task', task, 'report', 'cells', step='floorplan', index='0') == ['report.txt']


def test_metric_clear(chip):
    chip._record_metric('floorplan', '0', 'cells', 25, 'report.txt')
    assert chip.get('metric', 'cells', step='floorplan', index='0') == 25

    flow = chip.get('option', 'flow')
    tool = chip.get('flowgraph', flow, 'floorplan', '0', 'tool')
    task = chip.get('flowgraph', flow, 'floorplan', '0', 'task')
    assert chip.get('tool', tool, 'task', task, 'report', 'cells', step='floorplan', index='0') == ['report.txt']

    chip._clear_metric('floorplan', '0', 'cells')
    assert chip.get('metric', 'cells', step='floorplan', index='0') is None
    assert chip.get('tool', tool, 'task', task, 'report', 'cells', step='floorplan', index='0') == []
