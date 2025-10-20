import os

import pytest

import os.path

from datetime import datetime, timezone
from unittest.mock import patch, ANY

from siliconcompiler.apps import sc_issue

from siliconcompiler import Flowgraph, Project
from siliconcompiler.tools.builtin.nop import NOPTask


@pytest.fixture
def project(heartbeat_design):
    flow = Flowgraph("testflow")

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
     'sc_issue_heartbeat_job0_stepone_0_20200311-141213.tar.gz'),
    (['-cfg', 'build/heartbeat/job0/steptwo/0/outputs/heartbeat.pkg.json',
      '-arg_step', 'stepone', '-arg_index', '0'],
     'sc_issue_heartbeat_job0_stepone_0_20200311-141213.tar.gz'),
    (['-cfg', 'build/heartbeat/job0/stepone/0/outputs/heartbeat.pkg.json',
      '-arg_step', 'stepone', '-arg_index', '0'],
     'sc_issue_heartbeat_job0_stepone_0_20200311-141213.tar.gz'),
    (['-cfg', 'build/heartbeat/job0/heartbeat.pkg.json',
      '-arg_step', 'steptwo', '-arg_index', '0'],
     'sc_issue_heartbeat_job0_steptwo_0_20200311-141213.tar.gz')
])
def test_sc_issue_generate_success(flags,
                                   outputfile,
                                   monkeypatch,
                                   project):
    '''Test sc-issue app on a few sets of flags.'''

    monkeypatch.setattr('sys.argv', ['sc-issue'] + flags)
    with patch("siliconcompiler.utils.issue.datetime") as time:
        time.fromtimestamp = datetime.fromtimestamp
        time.now.return_value = datetime(2020, 3, 11, 14, 12, 13, tzinfo=timezone.utc)
        assert sc_issue.main() == 0
        time.now.assert_called()

    assert os.path.isfile(outputfile)


@pytest.mark.timeout(90)
@pytest.mark.parametrize('flags,args', [
    (['-cfg', 'build/heartbeat/job0/stepone/0/outputs/heartbeat.pkg.json'],
     ("stepone", "0", None,
      {"include_libraries": True, "include_specific_libraries": [], "hash_files": False})),
    (['-cfg', 'build/heartbeat/job0/steptwo/0/outputs/heartbeat.pkg.json',
      '-arg_step', 'stepone', '-arg_index', '0'],
     ("stepone", "0", None,
      {"include_libraries": True, "include_specific_libraries": [], "hash_files": False})),
    (['-cfg', 'build/heartbeat/job0/stepone/0/outputs/heartbeat.pkg.json',
      '-arg_step', 'stepone', '-arg_index', '0'],
     ("stepone", "0", None,
      {"include_libraries": True, "include_specific_libraries": [], "hash_files": False})),
    (['-cfg', 'build/heartbeat/job0/heartbeat.pkg.json',
      '-arg_step', 'steptwo', '-arg_index', '0'],
     ("steptwo", "0", None,
      {"include_libraries": True, "include_specific_libraries": [], "hash_files": False})),
    (['-cfg', 'build/heartbeat/job0/heartbeat.pkg.json',
      '-arg_step', 'steptwo', '-arg_index', '0', '-file', 'test.tar.gz'],
     ("steptwo", "0", "test.tar.gz",
      {"include_libraries": True, "include_specific_libraries": [], "hash_files": False})),
    (['-cfg', 'build/heartbeat/job0/heartbeat.pkg.json',
      '-arg_step', 'steptwo', '-arg_index', '0', '-hash_files'],
     ("steptwo", "0", None,
      {"include_libraries": True, "include_specific_libraries": [], "hash_files": True})),
    (['-cfg', 'build/heartbeat/job0/heartbeat.pkg.json',
      '-arg_step', 'steptwo', '-arg_index', '0', '-exclude_libraries'],
     ("steptwo", "0", None,
      {"include_libraries": False, "include_specific_libraries": [], "hash_files": False})),
    (['-cfg', 'build/heartbeat/job0/heartbeat.pkg.json',
      '-arg_step', 'steptwo', '-arg_index', '0', '-exclude_libraries',
      '-add_library', 'test0', '-add_library', 'test1'],
     ("steptwo", "0", None,
      {"include_libraries": False, "include_specific_libraries": ["test0", "test1"],
       "hash_files": False}))
])
def test_sc_issue_generate_call(flags,
                                args,
                                monkeypatch,
                                project):
    '''Test sc-issue app on a few sets of flags.'''

    monkeypatch.setattr('sys.argv', ['sc-issue'] + flags)
    with patch("siliconcompiler.apps.sc_issue.generate_testcase") as generate_testcase:
        assert sc_issue.main() == 0
        arg_step, arg_index, outfile, kwargs = args
        generate_testcase.assert_called_once_with(ANY, arg_step, arg_index, outfile, **kwargs)


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
