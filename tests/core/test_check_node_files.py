# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import pathlib
import pytest

from siliconcompiler.scheduler import _setup_workdir
from siliconcompiler.flowgraph import RuntimeFlowgraph


@pytest.fixture()
def fake_chip(gcd_chip):
    runtime = RuntimeFlowgraph(
        gcd_chip.schema.get("flowgraph", gcd_chip.get('option', 'flow'), field='schema'),
        from_steps=gcd_chip.get('option', 'from'),
        to_steps=gcd_chip.get('option', 'to'),
        prune_nodes=gcd_chip.get('option', 'prune'))

    for step, index in runtime.get_nodes():
        _setup_workdir(gcd_chip, step, index, False)
        workdir = pathlib.Path(gcd_chip.getworkdir(step=step, index=index))

        for nfile in (workdir / 'inputs' / f'{gcd_chip.design}.input',
                      workdir / 'outputs' / f'{gcd_chip.design}.output',
                      workdir / 'reports' / f'{gcd_chip.design}.rpt'):
            nfile.touch()

    return gcd_chip


def test_find_result(fake_chip):
    assert fake_chip.find_result('output', step='syn') is not None
    assert fake_chip.find_result('vg', step='syn') is None
    assert fake_chip.find_result('output', step='dne') is None
    assert fake_chip.find_result('vg', step='dne') is None


def test_find_result_with_index(fake_chip):
    assert fake_chip.find_result('output', step='syn', index='0') is not None
    assert fake_chip.find_result('output', step='syn', index='1') is None
    assert fake_chip.find_result('vg', step='syn', index='0') is None
    assert fake_chip.find_result('output', step='dne', index='0') is None
    assert fake_chip.find_result('vg', step='dne', index='0') is None


@pytest.mark.parametrize("path", ("inputs/gcd.input", "outputs/gcd.output", "reports/gcd.rpt"))
@pytest.mark.parametrize("step", ("syn", "floorplan.init", "write.gds"))
def test_find_node_file(fake_chip, path, step):
    assert fake_chip.find_node_file(path, step=step) is not None


@pytest.mark.parametrize("path", ("inputs/gcd.input0", "outputs/gcd.output0", "reports/gcd.rpt0"))
@pytest.mark.parametrize("step", ("syn0", "floorplan.init0", "write.gds0"))
def test_find_node_file_missing(fake_chip, path, step):
    assert fake_chip.find_node_file(path, step=step) is None
