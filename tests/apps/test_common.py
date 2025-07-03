import os
import time
import pytest

import os.path
from siliconcompiler.apps import _common


@pytest.fixture
def make_manifests():
    def impl(chip):
        for nodes in chip.get("flowgraph", "asicflow", field="schema").get_execution_order():
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
    assert set(_common.manifest_switches()) == {
        '-design',
        '-cfg',
        '-arg_step',
        '-arg_index',
        '-jobname'}


def test_get_manifests_single_design(gcd_chip, make_manifests):
    make_manifests(gcd_chip)

    manifests = _common._get_manifests(os.getcwd())
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

    manifests = _common._get_manifests(os.getcwd())
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

    manifests = _common._get_manifests(os.getcwd())
    assert len(manifests) == 2
    assert len(manifests["gcd"]) == 1
    assert len(manifests["gcd1"]) == 1
    assert len(manifests["gcd"]["job0"]) == 26
    assert len(manifests["gcd1"]["job0"]) == 26


def test_get_manifests_missingoutput(gcd_chip, make_manifests):
    make_manifests(gcd_chip)

    os.remove("build/gcd/job0/syn/0/outputs/gcd.pkg.json")

    manifests = _common._get_manifests(os.getcwd())
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
    assert _common.pick_manifest_from_file(gcd_chip, None, {}) is None


def test_pick_manifest_from_file_missing_file(gcd_chip):
    assert _common.pick_manifest_from_file(gcd_chip, "test.txt", {}) is None


def test_pick_manifest_from_file_empty_list(gcd_chip):
    with open("test.txt", "w") as f:
        f.write("testing")

    assert _common.pick_manifest_from_file(gcd_chip, "test.txt", {}) is None


def test_pick_manifest(gcd_chip, monkeypatch, caplogger):
    def get_manifests(pwd):
        return {}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(chip, src_file, manifests):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    log = caplogger(gcd_chip)
    assert _common.pick_manifest(gcd_chip) is None

    assert "Could not find manifest for gcd" in log()


def test_pick_manifest_noset_design(gcd_chip, monkeypatch, caplogger):
    def get_manifests(pwd):
        return {}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(chip, src_file, manifests):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    log = caplogger(gcd_chip)
    gcd_chip.set('design', _common.UNSET_DESIGN)
    assert _common.pick_manifest(gcd_chip) is None

    assert "Design name is not set" in log()


def test_pick_manifest_design_mismatch(gcd_chip, monkeypatch, caplogger):
    def get_manifests(pwd):
        return {"gcd0": {}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(chip, src_file, manifests):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    log = caplogger(gcd_chip)
    assert _common.pick_manifest(gcd_chip) is None

    assert gcd_chip.design == "gcd"

    assert "Could not find manifest for gcd" in log()


def test_pick_manifest_set_design(gcd_chip, monkeypatch):
    def get_manifests(pwd):
        return {"gcd": {"job0": {('syn', '0'): 'file'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(chip, src_file, manifests):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    with open('file', 'w') as f:
        f.write('test')

    gcd_chip.set('design', _common.UNSET_DESIGN)
    assert _common.pick_manifest(gcd_chip) == 'file'

    assert gcd_chip.design == "gcd"


def test_pick_manifest_newest_file(gcd_chip, monkeypatch):
    def get_manifests(pwd):
        return {"gcd": {"job0": {('syn', '0'): 'file', ('syn', '1'): 'file0'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(chip, src_file, manifests):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    with open('file', 'w') as f:
        f.write('test')

    time.sleep(1)

    with open('file0', 'w') as f:
        f.write('test0')

    gcd_chip.set('design', _common.UNSET_DESIGN)
    assert _common.pick_manifest(gcd_chip) == 'file0'

    assert gcd_chip.design == "gcd"


def test_pick_manifest_final_manifest(gcd_chip, monkeypatch):
    def get_manifests(pwd):
        return {"gcd": {"job0": {(None, None): 'file', ('syn', '1'): 'file0'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(chip, src_file, manifests):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    gcd_chip.set('design', _common.UNSET_DESIGN)
    assert _common.pick_manifest(gcd_chip) == 'file'

    assert gcd_chip.design == "gcd"


def test_pick_manifest_step_index_invalid(gcd_chip, monkeypatch, caplogger):
    def get_manifests(pwd):
        return {"gcd": {"job0": {(None, None): 'file', ('syn', '1'): 'file0'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(chip, src_file, manifests):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    log = caplogger(gcd_chip)
    gcd_chip.set('design', _common.UNSET_DESIGN)
    gcd_chip.set('arg', 'step', 'syn')
    gcd_chip.set('arg', 'index', '0')
    assert _common.pick_manifest(gcd_chip) is None

    assert gcd_chip.design == "gcd"

    assert "syn/0 is not a valid node." in log()


def test_pick_manifest_step_index_manifest(gcd_chip, monkeypatch):
    def get_manifests(pwd):
        return {"gcd": {"job0": {(None, None): 'file', ('syn', '1'): 'file0'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(chip, src_file, manifests):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    gcd_chip.set('design', _common.UNSET_DESIGN)
    gcd_chip.set('arg', 'step', 'syn')
    gcd_chip.set('arg', 'index', '1')
    assert _common.pick_manifest(gcd_chip) == 'file0'

    assert gcd_chip.design == "gcd"


def test_pick_manifest_step_index_invalid_default_index(gcd_chip, monkeypatch):
    def get_manifests(pwd):
        return {"gcd": {"job0": {(None, None): 'file', ('syn', '0'): 'file0'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(chip, src_file, manifests):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    gcd_chip.set('design', _common.UNSET_DESIGN)
    gcd_chip.set('arg', "step", 'syn')
    assert _common.pick_manifest(gcd_chip) == 'file0'

    assert gcd_chip.design == "gcd"


def test_pick_manifest_step_index_found_index(gcd_chip, monkeypatch):
    def get_manifests(pwd):
        return {"gcd": {"job0": {(None, None): 'file', ('syn', '1'): 'file0'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(chip, src_file, manifests):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    gcd_chip.set('design', _common.UNSET_DESIGN)
    gcd_chip.set('arg', "step", 'syn')
    assert _common.pick_manifest(gcd_chip) == 'file0'

    assert gcd_chip.design == "gcd"


def test_pick_manifest_step_index_invalid_combo(gcd_chip, monkeypatch, caplogger):
    def get_manifests(pwd):
        return {"gcd": {"job0": {(None, None): 'file', ('syn1', '1'): 'file0'}}}
    monkeypatch.setattr(_common, '_get_manifests', get_manifests)

    def pick_manifest_from_file(chip, src_file, manifests):
        return None
    monkeypatch.setattr(_common, 'pick_manifest_from_file', pick_manifest_from_file)

    log = caplogger(gcd_chip)
    gcd_chip.set('design', _common.UNSET_DESIGN)
    gcd_chip.set('arg', "step", 'syn')
    assert _common.pick_manifest(gcd_chip) is None

    assert gcd_chip.design == "gcd"

    assert "syn/0 is not a valid node." in log()
