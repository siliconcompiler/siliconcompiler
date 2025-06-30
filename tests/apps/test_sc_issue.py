import os

import pytest

import os.path

from unittest.mock import patch

from siliconcompiler.apps import sc_issue

from siliconcompiler import FlowgraphSchema, Project
from siliconcompiler.tools.builtin.nop import NOPTask


@pytest.fixture
def project(heartbeat_design):
    flow = FlowgraphSchema("testflow")

    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")

    proj = Project(heartbeat_design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    assert proj.run()

    return proj


@pytest.mark.parametrize('flags,outputfile', [
    (['-cfg', 'build/heartbeat/job0/stepone/0/outputs/heartbeat.pkg.json'],
     'sc_issue_heartbeat_job0_stepone_0_19691231-190020.tar.gz'),
    (['-cfg', 'build/heartbeat/job0/steptwo/0/outputs/heartbeat.pkg.json',
      '-arg_step', 'stepone', '-arg_index', '0'],
     'sc_issue_heartbeat_job0_stepone_0_19691231-190020.tar.gz'),
    (['-cfg', 'build/heartbeat/job0/stepone/0/outputs/heartbeat.pkg.json',
      '-arg_step', 'stepone', '-arg_index', '0'],
     'sc_issue_heartbeat_job0_stepone_0_19691231-190020.tar.gz'),
    (['-cfg', 'build/heartbeat/job0/heartbeat.pkg.json',
      '-arg_step', 'steptwo', '-arg_index', '0'],
     'sc_issue_heartbeat_job0_steptwo_0_19691231-190020.tar.gz')
])
def test_sc_issue_generate_success(flags,
                                   outputfile,
                                   monkeypatch,
                                   project):
    '''Test sc-issue app on a few sets of flags.'''

    monkeypatch.setattr('sys.argv', ['sc-issue'] + flags)
    with patch("time.time") as time:
        time.return_value = 20
        assert sc_issue.main() == 0
        time.assert_called()

    assert os.path.isfile(outputfile)


def test_sc_issue_generate_fail_step(monkeypatch, project, capsys):
    '''Test sc-issue app on a few sets of flags.'''

    monkeypatch.setattr('sys.argv', ['sc-issue', '-cfg', 'build/heartbeat/job0/heartbeat.pkg.json'])
    assert sc_issue.main() == 1
    assert "Unable to determine step from manifest" in capsys.readouterr().out


def test_sc_issue_generate_fail_index(monkeypatch, project, capsys):
    '''Test sc-issue app on a few sets of flags.'''

    monkeypatch.setattr('sys.argv', ['sc-issue', '-cfg', 'build/heartbeat/job0/heartbeat.pkg.json',
                                     '-arg_step', 'stepone'])
    assert sc_issue.main() == 1
    assert "Unable to determine index from manifest" in capsys.readouterr().out


def test_sc_issue_run(monkeypatch, project):
    '''Test sc-issue app on a few sets of flags.'''

    monkeypatch.setattr('sys.argv', ['sc-issue',
                                     '-cfg',
                                     'build/heartbeat/job0/stepone/0/outputs/heartbeat.pkg.json',
                                     '-file',
                                     'sc_issue.tar.gz'])
    assert sc_issue.main() == 0
    assert os.path.isfile("sc_issue.tar.gz")

    monkeypatch.setattr('sys.argv', ['sc-issue', '-run', '-file', 'sc_issue.tar.gz'])
    assert sc_issue.main() == 0
