import siliconcompiler
from siliconcompiler.flowgraph import gather_resume_failed_nodes
from siliconcompiler.scheduler import _setup_workdir
from siliconcompiler import NodeStatus

import os
import pytest
import shutil


@pytest.mark.eda
@pytest.mark.timeout(600)
def test_resume(gcd_chip):
    # Set a value that will cause place to break
    gcd_chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', 'asdf',
                 step='place', index='0')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run()

    # Ensure flow failed at placement, and store last modified time of floorplan
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    old_fp_mtime = os.path.getmtime(fp_result)

    assert gcd_chip.find_result('def', step='place') is None
    assert gcd_chip.find_result('gds', step='export') is None

    # Fix place step and re-run
    gcd_chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', '0.40',
                 step='place', index='0')
    gcd_chip.set('option', 'resume', True)
    gcd_chip.run()

    # Ensure floorplan did not get re-run
    fp_result = gcd_chip.find_result('def', step='floorplan')
    assert fp_result is not None
    assert os.path.getmtime(fp_result) == old_fp_mtime

    # Ensure flow finished successfully
    assert gcd_chip.find_result('def', step='place') is not None
    assert gcd_chip.find_result('gds', step='export') is not None


def test_resume_with_missing_node_missing_node(gcd_chip):
    flow = gcd_chip.get('option', 'flow')
    for step, index in gcd_chip.nodes_to_execute():
        _setup_workdir(gcd_chip, step, index, False)

        gcd_chip.set('flowgraph', flow, step, index, 'status', NodeStatus.SUCCESS)

        cfg = f"{gcd_chip._getworkdir(step=step, index=index)}/outputs/{gcd_chip.design}.pkg.json"
        gcd_chip.write_manifest(cfg)

    shutil.rmtree(gcd_chip._getworkdir(step='place', index='0'))

    gcd_chip.set('option', 'resume', True)

    resume_nodes = gather_resume_failed_nodes(
        gcd_chip,
        gcd_chip.get('option', 'flow'),
        gcd_chip.nodes_to_execute())
    assert ('import', '0') not in resume_nodes
    assert ('syn', '0') not in resume_nodes
    assert ('floorplan', '0') not in resume_nodes
    assert ('place', '0') in resume_nodes
    assert ('cts', '0') in resume_nodes
    assert ('route', '0') in resume_nodes
    assert ('dfm', '0') in resume_nodes
    assert ('export', '0') in resume_nodes
    assert ('export', '1') in resume_nodes


def test_resume_with_missing_node_failed_node(gcd_chip):
    flow = gcd_chip.get('option', 'flow')
    for step, index in gcd_chip.nodes_to_execute():
        _setup_workdir(gcd_chip, step, index, False)

        if step == 'place':
            gcd_chip.set('flowgraph', flow, step, index, 'status', NodeStatus.ERROR)
        else:
            gcd_chip.set('flowgraph', flow, step, index, 'status', NodeStatus.SUCCESS)

        cfg = f"{gcd_chip._getworkdir(step=step, index=index)}/outputs/{gcd_chip.design}.pkg.json"
        gcd_chip.write_manifest(cfg)

    gcd_chip.set('option', 'resume', True)

    resume_nodes = gather_resume_failed_nodes(
        gcd_chip,
        gcd_chip.get('option', 'flow'),
        gcd_chip.nodes_to_execute())
    assert ('import', '0') not in resume_nodes
    assert ('syn', '0') not in resume_nodes
    assert ('floorplan', '0') not in resume_nodes
    assert ('place', '0') in resume_nodes
    assert ('cts', '0') in resume_nodes
    assert ('route', '0') in resume_nodes
    assert ('dfm', '0') in resume_nodes
    assert ('export', '0') in resume_nodes
    assert ('export', '1') in resume_nodes


def test_resume_with_missing_node_no_failures(gcd_chip):
    flow = gcd_chip.get('option', 'flow')
    for step, index in gcd_chip.nodes_to_execute():
        _setup_workdir(gcd_chip, step, index, False)

        gcd_chip.set('flowgraph', flow, step, index, 'status', NodeStatus.SUCCESS)

        cfg = f"{gcd_chip._getworkdir(step=step, index=index)}/outputs/{gcd_chip.design}.pkg.json"
        gcd_chip.write_manifest(cfg)

    gcd_chip.set('option', 'resume', True)

    resume_nodes = gather_resume_failed_nodes(
        gcd_chip,
        gcd_chip.get('option', 'flow'),
        gcd_chip.nodes_to_execute())
    assert len(resume_nodes) == 0
