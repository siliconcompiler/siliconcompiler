# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
from siliconcompiler.scheduler import _setup_node

import os
import shutil

import pytest

from core.tools.fake import foo
from core.tools.fake import bar
from core.tools.fake import baz
from core.tools.echo import echo

from siliconcompiler.tools.builtin import nop
from siliconcompiler.targets import freepdk45_demo, gf180_demo


def test_check_manifest():
    chip = siliconcompiler.Chip('gcd')
    chip.use(freepdk45_demo)
    chip.input('examples/gcd/gcd.v')
    chip.set('option', 'to', ['syn'])

    for layer_nodes in chip.schema.get(
            "flowgraph", "asicflow", field="schema").get_execution_order():
        for step, index in layer_nodes:
            _setup_node(chip, step, index)

    chip.set('arg', 'step', None)
    chip.set('arg', 'index', None)
    assert chip.check_manifest()


@pytest.mark.eda
@pytest.mark.quick
def test_check_allowed_filepaths_pass(scroot):
    chip = siliconcompiler.Chip('gcd')

    chip.input(os.path.join(scroot, 'examples', 'gcd', 'gcd.v'))
    chip.use(freepdk45_demo)

    for layer_nodes in chip.schema.get(
            "flowgraph", "asicflow", field="schema").get_execution_order():
        for step, index in layer_nodes:
            _setup_node(chip, step, index)

    # collect input files
    cwd = os.getcwd()
    workdir = chip.getworkdir(step='import', index='0')
    os.makedirs(workdir)
    os.chdir(workdir)
    chip.collect()
    os.chdir(cwd)

    assert chip.check_manifest()


@pytest.mark.eda
@pytest.mark.quick
def test_check_allowed_filepaths_fail(scroot):
    chip = siliconcompiler.Chip('gcd')

    chip.input(os.path.join(scroot, 'examples', 'gcd', 'gcd.v'))
    chip.input('/random/abs/path/to/file.sdc')
    chip.set('input', 'constraint', 'sdc', False, field='copy')
    chip.use(freepdk45_demo)

    # collect input files
    workdir = chip.getworkdir(step='import', index='0')
    cwd = os.getcwd()
    os.makedirs(workdir)
    os.chdir(workdir)
    chip.collect()
    os.chdir(cwd)

    assert not chip.check_manifest()


@pytest.fixture
def merge_flow_chip():
    chip = siliconcompiler.Chip('test')

    flow = 'test'
    chip.node(flow, 'import', nop)
    chip.node(flow, 'parallel1', foo)
    chip.node(flow, 'parallel2', bar)
    chip.edge(flow, 'import', 'parallel1')
    chip.edge(flow, 'import', 'parallel2')

    chip.node(flow, 'export', baz)
    chip.edge(flow, 'parallel1', 'export')
    chip.edge(flow, 'parallel2', 'export')
    chip.set('option', 'flow', flow)

    chip.set('tool', 'foo', 'exe', 'foo')
    chip.set('tool', 'bar', 'exe', 'foo')
    chip.set('tool', 'baz', 'exe', 'baz')

    chip.set('tool', 'fake', 'task', 'baz', 'input', ['foo.out', 'bar.out'],
             step='export', index='0')

    return chip


def test_merged_graph_good(merge_flow_chip):
    merge_flow_chip.set('tool', 'fake', 'task', 'foo', 'output', 'bar.out',
                        step='parallel1', index='0')
    merge_flow_chip.set('tool', 'fake', 'task', 'bar', 'output', 'foo.out',
                        step='parallel2', index='0')

    assert merge_flow_chip.check_manifest()


def test_merged_graph_good_from_to():
    if not shutil.which("echo"):
        pytest.skip(reason="echo not found")

    chip = siliconcompiler.Chip('test')
    flow = 'test'
    chip.node(flow, 'import', nop)
    chip.node(flow, 'parallel1', echo)
    chip.node(flow, 'parallel2', echo)
    chip.node(flow, 'merge', echo)
    chip.node(flow, 'export', echo)
    chip.edge(flow, 'import', 'parallel1')
    chip.edge(flow, 'import', 'parallel2')
    chip.edge(flow, 'parallel1', 'merge')
    chip.edge(flow, 'parallel2', 'merge')
    chip.edge(flow, 'merge', 'export')
    chip.set('option', 'flow', flow)

    chip.run(raise_exception=True)

    chip.set('option', 'from', ['merge'])
    chip.set('option', 'to', ['export'])

    assert chip.check_manifest()


def test_merged_graph_bad_same(merge_flow_chip):
    # Two merged steps can't output the same thing
    merge_flow_chip.set('tool', 'fake', 'task', 'foo', 'output', 'foo.out',
                        step='parallel1', index='0')
    merge_flow_chip.set('tool', 'fake', 'task', 'bar', 'output', 'foo.out',
                        step='parallel2', index='0')

    assert not merge_flow_chip.check_manifest()


def test_merged_graph_bad_missing(merge_flow_chip):
    # bar doesn't provide necessary output
    merge_flow_chip.set('tool', 'fake', 'task', 'foo', 'output', 'foo.out',
                        step='parallel1', index='0')

    assert not merge_flow_chip.check_manifest()


def test_check_missing_task_module():
    chip = siliconcompiler.Chip('gcd')

    chip.use(freepdk45_demo)

    chip.set('flowgraph', chip.get('option', 'flow'), 'place.global', '0',
             'taskmodule', 'missing.place')

    assert not chip.check_manifest()


def test_check_missing_library():
    chip = siliconcompiler.Chip('test')
    chip.use(gf180_demo)
    chip.input('test.v')

    chip.add('option', 'library', 'sc_test')

    for layer_nodes in chip.schema.get(
            "flowgraph", "asicflow", field="schema").get_execution_order():
        for step, index in layer_nodes:
            _setup_node(chip, step, index)

    assert not chip.check_manifest()
