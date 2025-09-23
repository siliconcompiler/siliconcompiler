import os
import pytest

import os.path

from unittest.mock import patch

from siliconcompiler.apps import sc_show
from siliconcompiler.utils.paths import workdir, jobdir


@pytest.fixture
def make_manifests():
    def impl(project):
        for nodes in project.get("flowgraph", "asicflow", field="schema").get_execution_order():
            for step, index in nodes:
                for d in ('inputs', 'outputs'):
                    path = os.path.join(workdir(project, step=step, index=index), d)
                    os.makedirs(path, exist_ok=True)
                    project.write_manifest(os.path.join(path, f"{project.design.name}.pkg.json"))
        project.write_manifest(os.path.join(jobdir(project),
                                            f"{project.design.name}.pkg.json"))

    return impl


@pytest.mark.parametrize('flags', [
    [],
    ['-design', 'gcd'],
    ['-design', 'gcd',
     '-arg_step', 'floorplan.init'],
    ['-design', 'gcd',
     '-arg_step', 'floorplan.init',
     '-arg_index', '0'],
    ['-design', 'gcd']
])
def test_sc_show_design_only(flags, monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app on a few sets of flags.'''

    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show'] + flags)
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=False)


@pytest.mark.parametrize('flags', [
    [],
    ['-design', 'gcd'],
    ['-design', 'gcd',
     '-arg_step', 'floorplan.init'],
    ['-design', 'gcd',
     '-arg_step', 'floorplan.init',
     '-arg_index', '0'],
])
def test_sc_show_design_only_screenshot(flags, monkeypatch, make_manifests, asic_gcd, capsys):
    '''Test sc-show app on a few sets of flags.'''

    make_manifests(asic_gcd)

    with open("test.png", "w") as f:
        f.write("test")

    monkeypatch.setattr('sys.argv', ['sc-show', '-screenshot'] + flags)
    with patch('siliconcompiler.Project.show') as show:
        show.return_value = "test.png"
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=True)
    assert "Screenshot file: test.png" in capsys.readouterr().out


@pytest.mark.parametrize('flags', [
    ['build/heartbeat/job0/route.detailed/0/outputs/heartbeat.def'],
    ['build/heartbeat/job0/route.detailed/0/outputs/heartbeat.def'],
    ['build/heartbeat/job0/write.gds/0/outputs/heartbeat.gds'],
    ['build/heartbeat/job0/write.gds/0/inputs/heartbeat.def',
     '-cfg', 'build/heartbeat/job0/write.gds/0/outputs/heartbeat.pkg.json']
])
def test_sc_show(flags, monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app on a few sets of flags.'''

    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show'] + flags)
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(flags[0], extension=None, screenshot=False)


@pytest.mark.parametrize('flags', [
    ['-ext', 'gds'],
    ['-design', 'gcd', '-ext', 'gds'],
    ['-design', 'gcd',
     '-arg_step', 'floorplan.init', '-ext', 'def'],
    ['-design', 'gcd',
     '-arg_step', 'floorplan.init',
     '-arg_index', '0', '-ext', 'odb'],
])
def test_sc_show_ext(flags, monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app on a few sets of flags.'''

    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show'] + flags)
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=flags[-1], screenshot=False)


def test_sc_show_no_manifest(monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'test', '-arg_step', 'invalid'])
    assert sc_show.main() == 1
