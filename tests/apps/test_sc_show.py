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
                    project.write_manifest(os.path.join(path, f"{project.name}.pkg.json"))
        project.write_manifest(os.path.join(jobdir(project),
                                            f"{project.name}.pkg.json"))

    return impl


@pytest.mark.timeout(90)
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
        show.assert_called_once_with(None, extension=None, screenshot=False, tool=None)


@pytest.mark.timeout(90)
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
        show.assert_called_once_with(None, extension=None, screenshot=True, tool=None)
    assert "Screenshot file: test.png" in capsys.readouterr().out


@pytest.mark.parametrize('flags', [
    ['build/gcd/job0/route.detailed/0/outputs/gcd.def'],
    ['build/gcd/job0/route.detailed/0/outputs/gcd.def'],
    ['build/gcd/job0/write.gds/0/outputs/gcd.gds'],
    ['build/gcd/job0/write.gds/0/inputs/gcd.def',
     '-cfg', 'build/gcd/job0/write.gds/0/outputs/gcd.pkg.json']
])
def test_sc_show(flags, monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app on a few sets of flags.'''

    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show'] + flags)
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(flags[0], extension=None, screenshot=False, tool=None)


def test_sc_show_double_flags(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app on a few sets of flags.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', 'build/gcd/job0/write.gds/0/outputs/gcd.pkg.json',
                                     '-cfg', 'build/gcd/job0/write.gds/0/outputs/gcd.pkg.json'])
    assert sc_show.main() == 1


@pytest.mark.timeout(90)
def test_sc_show_with_tool_design_only(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool argument and design only.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-tool', 'klayout'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=False, tool='klayout')


@pytest.mark.timeout(90)
def test_sc_show_with_tool_and_file(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool argument and file path.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', 'build/gcd/job0/write.gds/0/outputs/gcd.gds',
                                     '-tool', 'openlane'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with('build/gcd/job0/write.gds/0/outputs/gcd.gds',
                                     extension=None, screenshot=False, tool='openlane')


@pytest.mark.timeout(90)
def test_sc_show_with_tool_and_screenshot(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool argument and screenshot.'''
    make_manifests(asic_gcd)

    with open("test.png", "w") as f:
        f.write("test")

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-screenshot',
                                     '-tool', 'gds2png'])
    with patch('siliconcompiler.Project.show') as show:
        show.return_value = "test.png"
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=True, tool='gds2png')


@pytest.mark.timeout(90)
def test_sc_show_with_tool_and_extension(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool argument and file extension.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-ext', 'odb',
                                     '-tool', 'openroad'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension='odb', screenshot=False, tool='openroad')


@pytest.mark.timeout(90)
def test_sc_show_with_tool_and_step_index(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool argument and step/index parameters.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-arg_step', 'route.detailed',
                                     '-arg_index', '0', '-tool', 'magic'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=False, tool='magic')


@pytest.mark.timeout(90)
def test_sc_show_with_tool_and_jobname(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool argument and jobname.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-jobname', 'rtl2gds',
                                     '-tool', 'klayout'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=False, tool='klayout')


@pytest.mark.timeout(90)
def test_sc_show_with_tool_and_cfg(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool argument and configuration file.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-cfg',
                                     'build/gcd/job0/write.gds/0/outputs/gcd.pkg.json',
                                     '-tool', 'magic'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=False, tool='magic')


@pytest.mark.timeout(90)
def test_sc_show_with_empty_tool(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with empty tool string.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-tool', ''])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=False, tool='')


@pytest.mark.timeout(90)
def test_sc_show_tool_with_all_parameters(monkeypatch, make_manifests, asic_gcd, capsys):
    '''Test sc-show app with tool and multiple other parameters.'''
    make_manifests(asic_gcd)

    with open("test.png", "w") as f:
        f.write("test")

    monkeypatch.setattr('sys.argv', ['sc-show', 'build/gcd/job0/write.gds/0/outputs/gcd.gds',
                                     '-ext', 'gds', '-screenshot', '-tool', 'klayout'])
    with patch('siliconcompiler.Project.show') as show:
        show.return_value = "test.png"
        assert sc_show.main() == 0
        show.assert_called_once_with('build/gcd/job0/write.gds/0/outputs/gcd.gds',
                                     extension='gds', screenshot=True, tool='klayout')
    assert "Screenshot file: test.png" in capsys.readouterr().out


@pytest.mark.timeout(90)
def test_sc_show_with_tool_task_format(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool/task format.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-tool', 'klayout/full'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension=None, screenshot=False, tool='klayout/full')


@pytest.mark.timeout(90)
def test_sc_show_with_tool_task_and_extension(monkeypatch, make_manifests, asic_gcd):
    '''Test sc-show app with tool/task format and extension.'''
    make_manifests(asic_gcd)

    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'gcd', '-ext', 'gds',
                                     '-tool', 'openroad/timing'])
    with patch('siliconcompiler.Project.show') as show:
        assert sc_show.main() == 0
        show.assert_called_once_with(None, extension='gds', screenshot=False,
                                     tool='openroad/timing')


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
        show.assert_called_once_with(None, extension=flags[-1], screenshot=False, tool=None)


def test_sc_show_no_manifest(monkeypatch):
    monkeypatch.setattr('sys.argv', ['sc-show', '-design', 'test', '-arg_step', 'invalid'])
    assert sc_show.main() == 1
