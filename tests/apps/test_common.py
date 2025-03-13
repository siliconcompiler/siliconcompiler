import os
import pytest

import os.path
from siliconcompiler.apps._common import manifest_switches, \
    _get_manifests, pick_manifest_from_file, pick_manifest
from siliconcompiler.flowgraph import _get_flowgraph_execution_order


@pytest.fixture
def make_manifests():
    def impl(chip):
        for nodes in _get_flowgraph_execution_order(chip, 'asicflow'):
            for step, index in nodes:
                for d in ('inputs', 'outputs'):
                    path = os.path.join(chip.getworkdir(step=step, index=index), d)
                    os.makedirs(path, exist_ok=True)
                    with open(os.path.join(path, f"{chip.design}.pkg.json"), "w") as f:
                        f.write('nothing')
        with open(os.path.join(chip.getworkdir(), f"{chip.design}.pkg.json"), "w") as f:
            f.write('nothing')

    return impl


def test_manifest_switches():
    assert set(manifest_switches()) == {
        '-design',
        '-cfg',
        '-arg_step',
        '-arg_index',
        '-jobname'}


def test_get_manifests_single_design(gcd_chip, make_manifests):
    make_manifests(gcd_chip)

    manifests = _get_manifests(os.getcwd())
    assert len(manifests) == 1
    assert len(manifests["gcd"]) == 1
    assert len(manifests["gcd"]["job0"]) == 26

    assert os.path.dirname(manifests["gcd"]["job0"][(None, None)]).endswith('job0')
    del manifests["gcd"]["job0"][(None, None)]

    for _, manifest in manifests["gcd"]["job0"].items():
        assert os.path.dirname(manifest).endswith('outputs')


def test_get_manifests_single_design_multiple_jobs(gcd_chip, make_manifests):
    make_manifests(gcd_chip)
    gcd_chip.set('option', 'jobname', 'job1')
    make_manifests(gcd_chip)

    manifests = _get_manifests(os.getcwd())
    assert len(manifests) == 1
    assert len(manifests["gcd"]) == 2
    assert len(manifests["gcd"]["job0"]) == 26
    assert len(manifests["gcd"]["job1"]) == 26

    assert os.path.dirname(manifests["gcd"]["job0"][(None, None)]).endswith('job0')
    del manifests["gcd"]["job0"][(None, None)]
    assert os.path.dirname(manifests["gcd"]["job1"][(None, None)]).endswith('job1')
    del manifests["gcd"]["job1"][(None, None)]

    for _, manifest in manifests["gcd"]["job0"].items():
        assert os.path.dirname(manifest).endswith('outputs')

    for _, manifest in manifests["gcd"]["job1"].items():
        assert os.path.dirname(manifest).endswith('outputs')


def test_get_manifests_multiple_designs(gcd_chip, make_manifests):
    make_manifests(gcd_chip)
    gcd_chip.set('design', 'gcd1')
    make_manifests(gcd_chip)

    manifests = _get_manifests(os.getcwd())
    assert len(manifests) == 2
    assert len(manifests["gcd"]) == 1
    assert len(manifests["gcd1"]) == 1
    assert len(manifests["gcd"]["job0"]) == 26
    assert len(manifests["gcd1"]["job0"]) == 26


def test_get_manifests_missingoutput(gcd_chip, make_manifests):
    make_manifests(gcd_chip)

    os.remove("build/gcd/job0/syn/0/outputs/gcd.pkg.json")

    manifests = _get_manifests(os.getcwd())
    assert len(manifests) == 1
    assert len(manifests["gcd"]) == 1
    assert len(manifests["gcd"]["job0"]) == 26

    assert os.path.dirname(manifests["gcd"]["job0"][(None, None)]).endswith('job0')
    del manifests["gcd"]["job0"][(None, None)]

    for node, manifest in manifests["gcd"]["job0"].items():
        if node == ('syn', '0'):
            assert os.path.dirname(manifest).endswith('inputs')
        else:
            assert os.path.dirname(manifest).endswith('outputs')


def test_pick_manifest_from_file_no_file(gcd_chip):
    assert pick_manifest_from_file(gcd_chip, None, {}) is None


def test_pick_manifest_from_file_missing_file(gcd_chip):
    assert pick_manifest_from_file(gcd_chip, "test.txt", {}) is None


def test_pick_manifest_from_file_empty_list(gcd_chip):
    with open("test.txt", "w") as f:
        f.write("testing")

    assert pick_manifest_from_file(gcd_chip, "test.txt", {}) is None
