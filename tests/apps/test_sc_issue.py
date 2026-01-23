import os
import sys

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


@pytest.mark.timeout(90)
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
     'sc_issue_heartbeat_job0_steptwo_0_20200311-141213.tar.gz'),
    (['-cfg', 'build/heartbeat/job0/steptwo/0/outputs/heartbeat.pkg.json'],
     'sc_issue_heartbeat_job0_steptwo_0_20200311-141213.tar.gz'),
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
def test_sc_issue_fail_on_no_cfg(monkeypatch, project):
    monkeypatch.setattr('sys.argv', ['sc-issue', 'build/heartbeat/job0/steptwo/0/outputs/heartbeat.pkg.json'])
    assert sc_issue.main() == 1


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


@pytest.mark.timeout(90)
def test_sc_issue_generate_fail_step(monkeypatch, project, capsys):
    '''Test sc-issue app on a few sets of flags.'''

    monkeypatch.setattr('sys.argv', ['sc-issue', '-cfg', 'build/heartbeat/job0/heartbeat.pkg.json'])
    assert sc_issue.main() == 1
    assert "Unable to determine step from manifest" in capsys.readouterr().out


@pytest.mark.timeout(90)
def test_sc_issue_generate_fail_index(monkeypatch, project, capsys):
    '''Test sc-issue app on a few sets of flags.'''

    monkeypatch.setattr('sys.argv', ['sc-issue', '-cfg', 'build/heartbeat/job0/heartbeat.pkg.json',
                                     '-arg_step', 'stepone'])
    assert sc_issue.main() == 1
    assert "Unable to determine index from manifest" in capsys.readouterr().out


@pytest.mark.timeout(90)
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


@pytest.mark.timeout(90)
def test_sc_issue_run_without_file(monkeypatch, project):
    '''Test sc-issue app fails when -run is used without -file.'''

    monkeypatch.setattr('sys.argv', ['sc-issue', '-run'])
    with pytest.raises(ValueError, match=r'-file must be provided'):
        sc_issue.main()


@pytest.mark.timeout(90)
def test_sc_issue_builddir_not_found(monkeypatch, tmp_path, project):
    '''Test sc-issue when builddir is not found in the path.'''
    import shutil

    # Copy the manifest to a completely different path
    manifest_path = 'build/heartbeat/job0/stepone/0/outputs/heartbeat.pkg.json'
    new_manifest_path = tmp_path / 'heartbeat.pkg.json'
    shutil.copy(manifest_path, new_manifest_path)

    monkeypatch.setattr('sys.argv', ['sc-issue', '-cfg', str(new_manifest_path),
                                     '-arg_step', 'stepone', '-arg_index', '0'])
    # The builddir won't be found so it will keep the original relative path
    # But the testcase should still be generated
    with patch("siliconcompiler.utils.issue.datetime") as time:
        time.fromtimestamp = datetime.fromtimestamp
        time.now.return_value = datetime(2020, 3, 11, 14, 12, 13, tzinfo=timezone.utc)
        assert sc_issue.main() == 0


@pytest.mark.timeout(90)
def test_sc_issue_as_main(monkeypatch, project):
    '''Test sc-issue app entry point - simply verify the function works.'''
    monkeypatch.setattr('sys.argv', ['sc-issue',
                                     '-cfg',
                                     'build/heartbeat/job0/stepone/0/outputs/heartbeat.pkg.json'])
    with patch("siliconcompiler.utils.issue.datetime") as time:
        time.fromtimestamp = datetime.fromtimestamp
        time.now.return_value = datetime(2020, 3, 11, 14, 12, 13, tzinfo=timezone.utc)
        # Test that main runs successfully
        retval = sc_issue.main()
        assert retval == 0


@pytest.mark.timeout(90)
def test_sc_issue_run_with_git_installed_version(monkeypatch, project):
    '''Test sc-issue run when the version doesn't have git commit info (installed version).'''
    import json
    import tarfile
    import shutil
    import os

    # First generate a testcase
    monkeypatch.setattr('sys.argv', ['sc-issue',
                                     '-cfg',
                                     'build/heartbeat/job0/stepone/0/outputs/heartbeat.pkg.json',
                                     '-file',
                                     'test_issue_orig.tar.gz'])
    with patch("siliconcompiler.utils.issue.datetime") as time:
        time.fromtimestamp = datetime.fromtimestamp
        time.now.return_value = datetime(2020, 3, 11, 14, 12, 13, tzinfo=timezone.utc)
        assert sc_issue.main() == 0

    # Extract and modify the issue.json to remove git commit
    test_dir = 'test_issue_orig'
    with tarfile.open('test_issue_orig.tar.gz', 'r:gz') as f:
        f.extractall(path='.')

    with open(f'{test_dir}/issue.json', 'r') as f:
        issue_info = json.load(f)

    # Remove the 'commit' key to test the else branch
    if 'commit' in issue_info['version']['git']:
        del issue_info['version']['git']['commit']

    with open(f'{test_dir}/issue.json', 'w') as f:
        json.dump(issue_info, f)

    # Create a new tarball with the modified data
    # The tarball name needs to match the expected directory structure
    new_tarball = 'test_issue_orig.tar.gz'
    if os.path.exists(new_tarball):
        os.remove(new_tarball)

    with tarfile.open(new_tarball, 'w:gz') as tar:
        tar.add(test_dir, arcname=test_dir)

    # Now run the modified testcase
    monkeypatch.setattr('sys.argv', ['sc-issue', '-run', '-file', new_tarball])
    assert sc_issue.main() == 0

    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)
