import logging
import os
import time
import pytest

import os.path
from siliconcompiler.apps import _common
from siliconcompiler.utils.paths import workdir, jobdir


@pytest.fixture
def make_manifests():
    def impl(project):
        for nodes in project.get("flowgraph", "asicflow", field="schema").get_execution_order():
            for step, index in nodes:
                for d in ('inputs', 'outputs'):
                    path = os.path.join(workdir(project, step=step, index=index), d)
                    os.makedirs(path, exist_ok=True)
                    with open(os.path.join(path, f"{project.name}.pkg.json"), "w") as f:
                        f.write('nothing')
        with open(os.path.join(jobdir(project), f"{project.name}.pkg.json"), "w") as f:
            f.write('nothing')

    return impl


def test_manifest_switches():
    assert set(_common.manifest_switches()) == {
        '-design',
        '-cfg',
        '-arg_step',
        '-arg_index',
        '-jobname'}


@pytest.mark.timeout(90)
def test_get_manifests_single_design(asic_gcd, make_manifests):
    make_manifests(asic_gcd)

    manifests = _common._get_manifests(os.getcwd())
    assert len(manifests) == 1
    assert len(manifests["gcd"]) == 1
    assert len(manifests["gcd"]["job0"]) == 20

    assert os.path.dirname(manifests["gcd"]["job0"][(None, None)]).endswith('job0')
    del manifests["gcd"]["job0"][(None, None)]

    for _, manifest in manifests["gcd"]["job0"].items():
        assert os.path.dirname(manifest).endswith('outputs')


@pytest.mark.timeout(90)
def test_get_manifests_single_design_multiple_jobs(asic_gcd, make_manifests):
    make_manifests(asic_gcd)
    asic_gcd.set('option', 'jobname', 'job1')
    make_manifests(asic_gcd)

    manifests = _common._get_manifests(os.getcwd())
    assert len(manifests) == 1
    assert len(manifests["gcd"]) == 2
    assert len(manifests["gcd"]["job0"]) == 20
    assert len(manifests["gcd"]["job1"]) == 20

    assert os.path.dirname(manifests["gcd"]["job0"][(None, None)]).endswith('job0')
    del manifests["gcd"]["job0"][(None, None)]
    assert os.path.dirname(manifests["gcd"]["job1"][(None, None)]).endswith('job1')
    del manifests["gcd"]["job1"][(None, None)]

    for _, manifest in manifests["gcd"]["job0"].items():
        assert os.path.dirname(manifest).endswith('outputs')

    for _, manifest in manifests["gcd"]["job1"].items():
        assert os.path.dirname(manifest).endswith('outputs')


@pytest.mark.timeout(90)
def test_get_manifests_multiple_designs(asic_gcd, asic_heartbeat, make_manifests):
    make_manifests(asic_gcd)
    make_manifests(asic_heartbeat)

    manifests = _common._get_manifests(os.getcwd())
    assert len(manifests) == 2
    assert len(manifests["gcd"]) == 1
    assert len(manifests["heartbeat"]) == 1
    assert len(manifests["gcd"]["job0"]) == 20
    assert len(manifests["heartbeat"]["job0"]) == 20


@pytest.mark.timeout(90)
def test_get_manifests_missingoutput(asic_gcd, make_manifests):
    make_manifests(asic_gcd)

    os.remove("build/gcd/job0/synthesis/0/outputs/gcd.pkg.json")

    manifests = _common._get_manifests(os.getcwd())
    assert len(manifests) == 1
    assert len(manifests["gcd"]) == 1
    assert len(manifests["gcd"]["job0"]) == 20

    assert os.path.dirname(manifests["gcd"]["job0"][(None, None)]).endswith('job0')
    del manifests["gcd"]["job0"][(None, None)]

    for node, manifest in manifests["gcd"]["job0"].items():
        if node == ('synthesis', '0'):
            assert os.path.dirname(manifest).endswith('inputs')
        else:
            assert os.path.dirname(manifest).endswith('outputs')


def test_pick_manifest_from_file_no_file(asic_gcd):
    assert _common.pick_manifest_from_file(asic_gcd, None, {}) is None


def test_pick_manifest_from_file_missing_file(asic_gcd):
    assert _common.pick_manifest_from_file(asic_gcd, "test.txt", {}) is None


def test_pick_manifest_from_file_empty_list(asic_gcd):
    with open("test.txt", "w") as f:
        f.write("testing")

    assert _common.pick_manifest_from_file(asic_gcd, "test.txt", {}) is None


def test_pick_manifest(asic_gcd, monkeypatch, caplog):
    def get_manifests(*args):
        return {}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(*args):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    monkeypatch.setattr(asic_gcd, "_Project__logger", logging.getLogger())
    asic_gcd.logger.setLevel(logging.INFO)
    assert _common.pick_manifest(asic_gcd) is None

    assert "Could not find any manifests for design \"gcd\"." in caplog.text


def test_pick_manifest_noset_design(asic_gcd, monkeypatch, caplog):
    def get_manifests(*args):
        return {}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(*args):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    monkeypatch.setattr(asic_gcd, "_Project__logger", logging.getLogger())
    asic_gcd.logger.setLevel(logging.INFO)
    asic_gcd.unset("option", "design")
    assert _common.pick_manifest(asic_gcd) is None

    assert "Design name is not set" in caplog.text


def test_pick_manifest_design_mismatch(asic_gcd, monkeypatch, caplog):
    def get_manifests(*args):
        return {"gcd0": {}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(*args):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    monkeypatch.setattr(asic_gcd, "_Project__logger", logging.getLogger())
    asic_gcd.logger.setLevel(logging.INFO)
    assert _common.pick_manifest(asic_gcd) is None

    assert asic_gcd.get("option", "design") == "gcd"

    assert "Could not find any manifests for design \"gcd\"." in caplog.text


def test_pick_manifest_set_design(asic_gcd, monkeypatch):
    def get_manifests(*args):
        return {"gcd": {"job0": {('syn', '0'): 'file'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(*args):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    with open('file', 'w') as f:
        f.write('test')

    asic_gcd.unset("option", "design")
    assert _common.pick_manifest(asic_gcd) == 'file'

    assert asic_gcd.get("option", "design") == "gcd"


def test_pick_manifest_newest_file(asic_gcd, monkeypatch):
    def get_manifests(*args):
        return {"gcd": {"job0": {('syn', '0'): 'file', ('syn', '1'): 'file0'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(*args):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    with open('file', 'w') as f:
        f.write('test')

    time.sleep(1)

    with open('file0', 'w') as f:
        f.write('test0')

    asic_gcd.unset("option", "design")
    assert _common.pick_manifest(asic_gcd) == 'file0'

    assert asic_gcd.get("option", "design") == "gcd"


def test_pick_manifest_final_manifest(asic_gcd, monkeypatch):
    def get_manifests(*args):
        return {"gcd": {"job0": {(None, None): 'file', ('syn', '1'): 'file0'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(*args):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    asic_gcd.unset("option", "design")
    assert _common.pick_manifest(asic_gcd) == 'file'

    assert asic_gcd.get("option", "design") == "gcd"


def test_pick_manifest_step_index_invalid(asic_gcd, monkeypatch, caplog):
    def get_manifests(*args):
        return {"gcd": {"job0": {(None, None): 'file', ('syn', '1'): 'file0'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(*args):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    monkeypatch.setattr(asic_gcd, "_Project__logger", logging.getLogger())
    asic_gcd.logger.setLevel(logging.INFO)
    asic_gcd.unset("option", "design")
    asic_gcd.set('arg', 'step', 'syn')
    asic_gcd.set('arg', 'index', '0')
    assert _common.pick_manifest(asic_gcd) is None

    assert asic_gcd.get("option", "design") == "gcd"

    assert "Node \"syn/0\" is not a valid node." in caplog.text


def test_pick_manifest_step_index_manifest(asic_gcd, monkeypatch):
    def get_manifests(*args):
        return {"gcd": {"job0": {(None, None): 'file', ('syn', '1'): 'file0'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(*args):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    asic_gcd.unset("option", "design")
    asic_gcd.set('arg', 'step', 'syn')
    asic_gcd.set('arg', 'index', '1')
    assert _common.pick_manifest(asic_gcd) == 'file0'

    assert asic_gcd.get("option", "design") == "gcd"


def test_pick_manifest_step_index_invalid_default_index(asic_gcd, monkeypatch):
    def get_manifests(*args):
        return {"gcd": {"job0": {(None, None): 'file', ('syn', '0'): 'file0'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(*args):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    asic_gcd.unset("option", "design")
    asic_gcd.set('arg', "step", 'syn')
    assert _common.pick_manifest(asic_gcd) == 'file0'

    assert asic_gcd.get("option", "design") == "gcd"


def test_pick_manifest_step_index_found_index(asic_gcd, monkeypatch):
    def get_manifests(*args):
        return {"gcd": {"job0": {(None, None): 'file', ('syn', '1'): 'file0'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(*args):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    asic_gcd.unset("option", "design")
    asic_gcd.set('arg', "step", 'syn')
    assert _common.pick_manifest(asic_gcd) == 'file0'

    assert asic_gcd.get("option", "design") == "gcd"


def test_pick_manifest_step_index_invalid_combo(asic_gcd, monkeypatch, caplog):
    def get_manifests(*args):
        return {"gcd": {"job0": {(None, None): 'file', ('syn1', '1'): 'file0'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(*args):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    monkeypatch.setattr(asic_gcd, "_Project__logger", logging.getLogger())
    asic_gcd.logger.setLevel(logging.INFO)
    asic_gcd.unset("option", "design")
    asic_gcd.set('arg', "step", 'syn')
    assert _common.pick_manifest(asic_gcd) is None

    assert asic_gcd.get("option", "design") == "gcd"

    assert "Node \"syn/0\" is not a valid node." in caplog.text


@pytest.mark.timeout(90)
def test_pick_manifest_from_file_found(asic_gcd, make_manifests, tmp_path):
    '''Test finding manifest based on file in same directory.'''
    make_manifests(asic_gcd)

    # Create a test file in the same directory as the manifest
    manifest_path = os.path.join(os.getcwd(), 'build', 'gcd', 'job0', 'gcd.pkg.json')
    manifest_dir = os.path.dirname(manifest_path)
    test_file = os.path.join(manifest_dir, 'test.gds')
    with open(test_file, 'w') as f:
        f.write('test')

    manifests = _common._get_manifests(os.getcwd())
    result = _common.pick_manifest_from_file(asic_gcd, test_file, manifests)

    assert result is not None
    assert os.path.dirname(result) == manifest_dir


@pytest.mark.timeout(90)
def test_pick_manifest_from_file_in_outputs(asic_gcd, make_manifests, tmp_path):
    '''Test finding manifest when file is in outputs directory.'''
    make_manifests(asic_gcd)

    # Create test file in outputs directory alongside manifest
    outputs_manifest = os.path.join(os.getcwd(), 'build', 'gcd', 'job0', 'synthesis', '0',
                                    'outputs', 'gcd.pkg.json')
    outputs_dir = os.path.dirname(outputs_manifest)
    test_file = os.path.join(outputs_dir, 'gcd.v')
    with open(test_file, 'w') as f:
        f.write('test')

    manifests = _common._get_manifests(os.getcwd())
    result = _common.pick_manifest_from_file(asic_gcd, test_file, manifests)

    assert result is not None
    assert outputs_dir in result


@pytest.mark.timeout(90)
def test_pick_manifest_jobname_inference(asic_gcd, monkeypatch):
    '''Test jobname inference when only one job exists.'''
    def get_manifests(*args):
        return {"gcd": {"job0": {(None, None): 'file'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(*args):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    asic_gcd.set('option', 'design', 'gcd')
    # Don't set jobname - it should be inferred
    result = _common.pick_manifest(asic_gcd)

    assert result == 'file'
    # jobname should remain unset or be inferred internally
    assert asic_gcd.get("option", "design") == "gcd"


@pytest.mark.timeout(90)
def test_pick_manifest_infer_design_from_filename(asic_gcd, monkeypatch):
    '''Test inferring design name from source file when design not set.'''
    def get_manifests(*args):
        return {"gcd": {"job0": {(None, None): 'file'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(*args):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    asic_gcd.unset('option', 'design')
    result = _common.pick_manifest(asic_gcd, src_file='gcd.v')

    assert result == 'file'
    assert asic_gcd.get("option", "design") == "gcd"
