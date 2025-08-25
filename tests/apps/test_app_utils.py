import pytest
import sys

import os.path

from siliconcompiler import FlowgraphSchema, Project
from siliconcompiler.tools.builtin.nop import NOPTask
from siliconcompiler.apps.utils import summarize, replay


@pytest.fixture
def gcd_nop_project_run(gcd_design):
    project = Project(gcd_design)
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    flow = FlowgraphSchema("nopflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    project.set_flow(flow)

    project.set('option', 'nodisplay', True)
    project.set('option', 'quiet', True)

    assert project.run()

    return project


def test_summarize_cfg(monkeypatch, gcd_nop_project_run, capsys):
    '''Tests that sc summarizes a cfg.'''

    gcd_nop_project_run.write_manifest('test.json')
    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv', [summarize.__name__, '-cfg', 'test.json'])
    assert summarize.main() == 0

    assert "stepone/0  steptwo/0" in capsys.readouterr().out


def test_summarize_cfg_no_cfg(monkeypatch):
    '''Tests that sc summarizes a cfg.'''

    monkeypatch.setattr('sys.argv', [summarize.__name__])
    assert summarize.main() == 1


@pytest.mark.skipif(sys.platform == "win32", reason="Not supported on windows")
def test_replay_cfg_cli_error(monkeypatch, run_cli, gcd_nop_project_run):
    '''Tests that sc generates a replay script.'''

    gcd_nop_project_run.write_manifest('test.json')
    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv',
                        [replay.__name__, '-cfg', 'test.json', '-file', 'test_replay.sh'])
    assert replay.main() == 0

    assert os.path.isfile('test_replay.sh')

    run_cli(['./test_replay.sh', '-error'], retcode=1)


@pytest.mark.skipif(sys.platform == "win32", reason="Not supported on windows")
def test_replay_cfg_help(monkeypatch, run_cli, gcd_nop_project_run):
    '''Tests that sc generates a replay script.'''

    gcd_nop_project_run.write_manifest('test.json')
    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv',
                        [replay.__name__, '-cfg', 'test.json', '-file', 'test_replay.sh'])
    assert replay.main() == 0

    assert os.path.isfile('test_replay.sh')

    proc = run_cli(['./test_replay.sh', '-help'])

    assert proc.returncode == 0

    output = proc.stdout
    assert "-dir=DIR" in output
    assert "-venv=DIR" in output
    assert "-print_tools" in output
    assert "-extract_only" in output
    assert "-setup_only" in output
    assert "-help" in output


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.skipif(sys.platform == "win32", reason="Not supported on windows")
def test_replay_cfg_print_tools(monkeypatch, run_cli, asic_gcd):
    '''Tests that sc generates a replay script.'''

    asic_gcd.set("option", "to", "synthesis")
    assert asic_gcd.run()

    asic_gcd.write_manifest('test.json')
    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv',
                        [replay.__name__, '-cfg', 'test.json', '-file', 'test_replay.sh'])
    assert replay.main() == 0

    assert os.path.isfile('test_replay.sh')

    proc = run_cli(['./test_replay.sh', '-print_tools'])
    assert proc.returncode == 0

    assert "yosys: " in proc.stdout


@pytest.mark.skipif(sys.platform == "win32", reason="Not supported on windows")
@pytest.mark.skipif(sys.platform == "darwin", reason="realpath not available in bash on macos")
def test_replay_cfg_setup(monkeypatch, run_cli, gcd_nop_project_run):
    '''Tests that sc generates a replay script.'''

    gcd_nop_project_run.write_manifest('test.json')
    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv',
                        [replay.__name__, '-cfg', 'test.json', '-file', 'test_replay.sh'])
    assert replay.main() == 0

    assert os.path.isfile('test_replay.sh')

    # Remove slow pip install
    with open("test_replay.sh", "r") as fin:
        script = fin.read().splitlines()
    script[script.index("pip3 install -r requirements.txt")] = "# removed pip install"
    with open("test_replay.sh", "w") as fout:
        fout.write("\n".join(script))

    proc = run_cli(['./test_replay.sh',
                    '-dir=replay_dir',
                    '-venv=env',
                    '-assert_python',
                    '-setup_only'])
    assert proc.returncode == 0

    assert os.path.isdir('replay_dir')
    assert os.path.isdir('replay_dir/env')

    assert os.path.isfile('replay_dir/requirements.txt')
    assert os.path.isfile('replay_dir/sc_manifest.json')
    assert os.path.isfile('replay_dir/replay.py')


def test_replay_cfg_no_cfg(monkeypatch, gcd_nop_project_run):
    '''Tests that sc generates a replay script.'''

    gcd_nop_project_run.write_manifest('test.json')
    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv',
                        [replay.__name__, '-file', 'test_replay.sh'])

    assert replay.main() == 1

    assert not os.path.isfile('test_replay.sh')


def test_replay_cfg_no_file(monkeypatch, gcd_nop_project_run):
    '''Tests that sc generates a replay script.'''

    gcd_nop_project_run.write_manifest('test.json')
    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv',
                        [replay.__name__, '-cfg', 'test.json'])

    assert not os.path.isfile('replay.sh')

    assert replay.main() == 0

    assert os.path.isfile('replay.sh')
