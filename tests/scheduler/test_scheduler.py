import logging
import os
import pytest
import time

import os.path

from unittest.mock import patch

from siliconcompiler import Project, Flowgraph, Design, NodeStatus
from siliconcompiler.scheduler import Scheduler
from siliconcompiler.schema import EditableSchema, Parameter

from siliconcompiler.tools.builtin.nop import NOPTask
from siliconcompiler.utils.paths import jobdir
from siliconcompiler.tools import get_task


@pytest.fixture
def gcd_nop_project(gcd_design):
    project = Project(gcd_design)
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    flow = Flowgraph("nopflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.node("stepthree", NOPTask())
    flow.node("stepfour", NOPTask())
    flow.edge("stepone", "steptwo")
    flow.edge("steptwo", "stepthree")
    flow.edge("stepthree", "stepfour")
    project.set_flow(flow)

    return project


@pytest.fixture
def remove_display_environment():
    names_to_remove = {'DISPLAY', 'WAYLAND_DISPLAY'}
    return {k: v for k, v in os.environ.items() if k not in names_to_remove}


@pytest.fixture
def basic_project():
    flow = Flowgraph("test")
    flow.node("stepone", NOPTask())
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    return proj


@pytest.fixture
def basic_project_no_flow():
    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")
    proj = Project(design)
    proj.add_fileset("rtl")

    return proj


def test_init_no_flow():
    with pytest.raises(ValueError, match="flow must be specified"):
        Scheduler(Project(Design("testdesign")))


def test_init_flow_not_defined(basic_project):
    basic_project.set("option", "flow", "testflow")
    with pytest.raises(ValueError, match="flow is not defined"):
        Scheduler(basic_project)


def test_init_flow_not_valid(basic_project):
    with patch("siliconcompiler.flowgraph.Flowgraph.validate") as call:
        call.return_value = False
        with pytest.raises(ValueError, match="test flowgraph contains errors and cannot be run."):
            Scheduler(basic_project)


def test_init_flow_runtime_not_valid(basic_project):
    with patch("siliconcompiler.flowgraph.Flowgraph.validate") as call0, \
         patch("siliconcompiler.flowgraph.RuntimeFlowgraph.validate") as call1:
        call0.return_value = True
        call1.return_value = False
        with pytest.raises(ValueError, match="test flowgraph contains errors and cannot be run."):
            Scheduler(basic_project)


def test_check_display_run(basic_project):
    # Checks if check_display() is called during run()
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_display",
               autospec=True) as call:
        scheduler.run()
        call.assert_called_once()


@patch('sys.platform', 'linux')
def test_check_display_nodisplay(basic_project, remove_display_environment, monkeypatch, caplog):
    # Checks if the nodisplay option is set
    # On linux system without display
    monkeypatch.setattr(basic_project, "_Project__logger", logging.getLogger())
    basic_project.logger.setLevel(logging.INFO)

    basic_project.set("option", "nodisplay", False)
    assert basic_project.get('option', 'nodisplay') is False

    scheduler = Scheduler(basic_project)
    with patch.dict(os.environ, remove_display_environment, clear=True):
        scheduler._Scheduler__check_display()
    assert basic_project.get('option', 'nodisplay') is True
    assert "Environment variable $DISPLAY or $WAYLAND_DISPLAY not set" in caplog.text
    assert "Setting [option,nodisplay] to True" in caplog.text


@patch('sys.platform', 'linux')
@pytest.mark.parametrize("env,value", [("DISPLAY", ":0"), ("WAYLAND_DISPLAY", "wayland-0")])
def test_check_display_with_display(basic_project, remove_display_environment, env, value):
    # Checks that the nodisplay option is not set
    # On linux system with display

    basic_project.set("option", "nodisplay", False)
    assert basic_project.get('option', 'nodisplay') is False

    scheduler = Scheduler(basic_project)
    remove_display_environment[env] = value
    with patch.dict(os.environ, remove_display_environment, clear=True):
        scheduler._Scheduler__check_display()
    assert basic_project.get('option', 'nodisplay') is False


@patch('sys.platform', 'darwin')
def test_check_display_with_display_macos(basic_project, remove_display_environment):
    # Checks that the nodisplay option is not set
    # On macos system
    basic_project.set("option", "nodisplay", False)
    assert basic_project.get('option', 'nodisplay') is False

    scheduler = Scheduler(basic_project)
    with patch.dict(os.environ, remove_display_environment, clear=True):
        scheduler._Scheduler__check_display()
    assert basic_project.get('option', 'nodisplay') is False


@patch('sys.platform', 'win32')
def test_check_display_with_display_windows(basic_project, remove_display_environment):
    # Checks that the nodisplay option is not set
    # On windows system
    basic_project.set("option", "nodisplay", False)
    assert basic_project.get('option', 'nodisplay') is False

    scheduler = Scheduler(basic_project)
    with patch.dict(os.environ, remove_display_environment, clear=True):
        scheduler._Scheduler__check_display()
    assert basic_project.get('option', 'nodisplay') is False


def test_increment_job_name_run(basic_project):
    # Checks if __increment_job_name() is called during run()
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.scheduler.Scheduler._Scheduler__increment_job_name",
               autospec=True) as call:
        scheduler.run()
        call.assert_called_once()


def test_increment_job_name_with_cleanout(basic_project):
    basic_project.set('option', 'clean', False)

    scheduler = Scheduler(basic_project)

    assert scheduler._Scheduler__increment_job_name() is False


def test_increment_job_name_with_clean_but_not_increment(basic_project):
    basic_project.set('option', 'clean', True)
    basic_project.set('option', 'jobincr', False)

    scheduler = Scheduler(basic_project)

    assert scheduler._Scheduler__increment_job_name() is False


def test_increment_job_name_default(basic_project):
    basic_project.set('option', 'clean', True)
    basic_project.set('option', 'jobincr', True)

    scheduler = Scheduler(basic_project)

    os.makedirs(jobdir(basic_project), exist_ok=True)

    assert basic_project.get("option", "jobname") == "job0"
    assert scheduler._Scheduler__increment_job_name() is True
    assert basic_project.get("option", "jobname") == "job1"


def test_increment_job_name_default_no_dir(basic_project):
    basic_project.set('option', 'clean', True)
    basic_project.set('option', 'jobincr', True)

    scheduler = Scheduler(basic_project)

    assert basic_project.get("option", "jobname") == "job0"
    assert scheduler._Scheduler__increment_job_name() is False
    assert basic_project.get("option", "jobname") == "job0"


@pytest.mark.parametrize("prev_name,new_name", [
    ("test0", "test1"),
    ("test00", "test1"),
    ("test10", "test11"),
    ("test", "test1"),
    ("junkname0withnumbers1", "junkname0withnumbers2")
])
def test_increment_job_name(basic_project, prev_name, new_name):
    basic_project.set('option', 'clean', True)
    basic_project.set('option', 'jobincr', True)

    basic_project.set('option', 'jobname', prev_name)
    scheduler = Scheduler(basic_project)

    os.makedirs(jobdir(basic_project), exist_ok=True)

    assert basic_project.get("option", "jobname") == prev_name
    assert scheduler._Scheduler__increment_job_name() is True
    assert basic_project.get("option", "jobname") == new_name


def test_clean_build_dir_full(basic_project):
    basic_project.set('option', 'clean', True)

    scheduler = Scheduler(basic_project)

    os.makedirs(jobdir(basic_project), exist_ok=True)
    os.makedirs(os.path.join(jobdir(basic_project), "rmthis"), exist_ok=True)
    with open(os.path.join(jobdir(basic_project), "job.log"), "w") as f:
        f.write("test")

    with patch("shutil.rmtree", autospec=True) as rmtree, \
            patch("os.remove") as remove:
        scheduler._Scheduler__clean_build_dir_full()
        rmtree.assert_called_once()
        remove.assert_called_once()


def test_clean_build_dir_full_keep_log(basic_project):
    basic_project.set('option', 'clean', True)

    scheduler = Scheduler(basic_project)

    os.makedirs(jobdir(basic_project), exist_ok=True)
    os.makedirs(os.path.join(jobdir(basic_project), "rmthis"), exist_ok=True)
    with open(os.path.join(jobdir(basic_project), "job.log"), "w") as f:
        f.write("test")

    with patch("shutil.rmtree", autospec=True) as rmtree, \
            patch("os.remove") as remove:
        scheduler._Scheduler__clean_build_dir_full(recheck=True)
        rmtree.assert_called_once()
        remove.assert_not_called()


def test_clean_build_dir_full_keep_log_rm_old_log(basic_project):
    basic_project.set('option', 'clean', True)

    scheduler = Scheduler(basic_project)

    os.makedirs(jobdir(basic_project), exist_ok=True)
    os.makedirs(os.path.join(jobdir(basic_project), "rmthis"), exist_ok=True)
    with open(os.path.join(jobdir(basic_project), "job.log"), "w") as f:
        f.write("test")
    with open(os.path.join(jobdir(basic_project), "job.log.bak"), "w") as f:
        f.write("test")

    with patch("shutil.rmtree", autospec=True) as rmtree, \
            patch("os.remove") as remove:
        scheduler._Scheduler__clean_build_dir_full(recheck=True)
        rmtree.assert_called_once()
        remove.assert_called_once_with(os.path.join(jobdir(basic_project), "job.log.bak"))


def test_clean_build_dir_full_with_from(basic_project):
    basic_project.set('option', 'clean', True)
    basic_project.set('option', 'from', 'stepone')

    scheduler = Scheduler(basic_project)

    os.makedirs(jobdir(basic_project), exist_ok=True)
    assert os.path.isdir(jobdir(basic_project))

    with patch("shutil.rmtree", autospec=True) as rmtree:
        scheduler._Scheduler__clean_build_dir_full()
        rmtree.assert_not_called()


def test_clean_build_dir_full_do_nothing(basic_project):
    basic_project.set('option', 'clean', False)

    scheduler = Scheduler(basic_project)

    os.makedirs(jobdir(basic_project), exist_ok=True)

    with patch("shutil.rmtree", autospec=True) as rmtree:
        scheduler._Scheduler__clean_build_dir_full()
        rmtree.assert_not_called()


def test_clean_build_dir_full_remote(basic_project):
    basic_project.set('option', 'clean', True)
    basic_project.set('record', 'remoteid', 'blah')

    scheduler = Scheduler(basic_project)

    os.makedirs(jobdir(basic_project), exist_ok=True)

    with patch("shutil.rmtree", autospec=True) as rmtree:
        scheduler._Scheduler__clean_build_dir_full()
        rmtree.assert_not_called()


def test_check_manifest_pass(basic_project):
    """
    Verifies that Scheduler.run() invokes check_manifest() and proceeds when the manifest check returns `True`.
    """
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.scheduler.Scheduler.check_manifest",
               autospec=True) as call:
        call.return_value = True
        scheduler.run()
        call.assert_called_once()


def test_check_manifest_fail(basic_project):
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.scheduler.Scheduler.check_manifest",
               autospec=True) as call:
        call.return_value = False
        with pytest.raises(RuntimeError, match='check_manifest\\(\\) failed'):
            scheduler.run()
        call.assert_called_once()


def test_check_flowgraph_io_basic(basic_project, monkeypatch, caplog):
    monkeypatch.setattr(basic_project, "_Project__logger", logging.getLogger())
    basic_project.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project)

    assert scheduler._Scheduler__check_flowgraph_io() is True
    assert caplog.text == ""


def test_check_flowgraph_io_with_files(basic_project_no_flow, monkeypatch, caplog):
    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    basic_project_no_flow.set_flow(flow)

    monkeypatch.setattr(basic_project_no_flow, "_Project__logger", logging.getLogger())
    basic_project_no_flow.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project_no_flow)

    nop = get_task(basic_project_no_flow, filter=NOPTask)
    nop.add_output_file("test.v", step="stepone", index="0")
    nop.add_input_file("test.v", step="steptwo", index="0")

    assert scheduler._Scheduler__check_flowgraph_io() is True
    assert caplog.text == ""


def test_check_flowgraph_io_with_files_join(basic_project_no_flow, monkeypatch, caplog):
    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.node("dojoin", NOPTask())
    flow.node("postjoin", NOPTask())
    flow.edge("stepone", "dojoin")
    flow.edge("steptwo", "dojoin")
    flow.edge("dojoin", "postjoin")
    basic_project_no_flow.set_flow(flow)

    monkeypatch.setattr(basic_project_no_flow, "_Project__logger", logging.getLogger())
    basic_project_no_flow.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project_no_flow)

    nop = get_task(basic_project_no_flow, filter=NOPTask)
    nop.add_output_file("a.v", step="stepone", index="0")
    nop.add_output_file("b.v", step="steptwo", index="0")
    nop.add_input_file("a.v", step="dojoin", index="0")
    nop.add_input_file("b.v", step="dojoin", index="0")
    nop.add_output_file("a.v", step="dojoin", index="0")
    nop.add_output_file("b.v", step="dojoin", index="0")
    nop.add_input_file("a.v", step="postjoin", index="0")
    nop.add_input_file("b.v", step="postjoin", index="0")

    assert scheduler._Scheduler__check_flowgraph_io() is True
    assert caplog.text == ""


def test_check_flowgraph_io_with_files_join_extra_files(basic_project_no_flow, monkeypatch, caplog):
    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.node("dojoin", NOPTask())
    flow.node("postjoin", NOPTask())
    flow.edge("stepone", "dojoin")
    flow.edge("steptwo", "dojoin")
    flow.edge("dojoin", "postjoin")
    basic_project_no_flow.set_flow(flow)

    monkeypatch.setattr(basic_project_no_flow, "_Project__logger", logging.getLogger())
    basic_project_no_flow.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project_no_flow)

    nop = get_task(basic_project_no_flow, filter=NOPTask)
    nop.add_output_file("a.v", step="stepone", index="0")
    nop.add_output_file("common.v", step="stepone", index="0")
    nop.add_output_file("b.v", step="steptwo", index="0")
    nop.add_output_file("common.v", step="stepone", index="0")
    nop.add_input_file("common.v", step="dojoin", index="0")
    nop.add_output_file("common.v", step="dojoin", index="0")
    nop.add_input_file("common.v", step="postjoin", index="0")

    assert scheduler._Scheduler__check_flowgraph_io() is True
    assert caplog.text == ""


def test_check_flowgraph_io_with_files_missing_input(basic_project_no_flow, monkeypatch, caplog):
    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    basic_project_no_flow.set_flow(flow)

    monkeypatch.setattr(basic_project_no_flow, "_Project__logger", logging.getLogger())
    basic_project_no_flow.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project_no_flow)

    nop = get_task(basic_project_no_flow, filter=NOPTask)
    nop.add_output_file("test.v", step="stepone", index="0")
    nop.add_input_file("test.v", step="steptwo", index="0")
    nop.add_input_file("missing.v", step="steptwo", index="0")

    assert scheduler._Scheduler__check_flowgraph_io() is False
    assert "Invalid flow: steptwo/0 will not receive required input missing.v" in caplog.text


def test_check_flowgraph_io_with_files_multple_input(basic_project_no_flow, monkeypatch, caplog):
    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask(), index=0)
    flow.node("stepone", NOPTask(), index=1)
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo", tail_index=0)
    flow.edge("stepone", "steptwo", tail_index=1)
    basic_project_no_flow.set_flow(flow)

    monkeypatch.setattr(basic_project_no_flow, "_Project__logger", logging.getLogger())
    basic_project_no_flow.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project_no_flow)

    nop = get_task(basic_project_no_flow, filter=NOPTask)
    nop.add_output_file("test.v", step="stepone", index="0")
    nop.add_output_file("test.v", step="stepone", index="1")
    nop.add_input_file("test.v", step="steptwo", index="0")

    assert scheduler._Scheduler__check_flowgraph_io() is False
    assert "Invalid flow: steptwo/0 receives test.v from multiple input tasks" in caplog.text


def test_rerun(gcd_nop_project):
    '''Regression test for #458.'''

    gcd_nop_project.set('option', 'to', ['stepthree'])
    assert gcd_nop_project.run()
    run_copy = gcd_nop_project.copy()
    time.sleep(1)  # delay to ensure timestamps differ
    gcd_nop_project.set('option', 'from', ['steptwo'])
    gcd_nop_project.set('option', 'to', ['steptwo'])
    assert gcd_nop_project.run()

    assert run_copy.history("job0").get("record", "endtime", step="steptwo", index="0") != \
        gcd_nop_project.history("job0").get("record", "endtime", step="steptwo", index="0")

    assert run_copy.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SUCCESS
    assert run_copy.history("job0").get("record", "status", step="stepthree", index="0") == \
        NodeStatus.SUCCESS

    assert gcd_nop_project.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SUCCESS
    assert gcd_nop_project.history("job0").get("record", "status", step="stepthree", index="0") == \
        NodeStatus.PENDING


def test_resume_normal(gcd_nop_project):
    assert gcd_nop_project.run()
    run_copy = gcd_nop_project.copy()
    time.sleep(1)  # delay to ensure timestamps differ
    assert gcd_nop_project.run()

    assert run_copy.history("job0").get("record", "endtime", step="steptwo", index="0") == \
        gcd_nop_project.history("job0").get("record", "endtime", step="steptwo", index="0")

    assert run_copy.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SUCCESS
    assert run_copy.history("job0").get("record", "status", step="stepthree", index="0") == \
        NodeStatus.SUCCESS
    assert gcd_nop_project.history("job0").get("record", "status", step="stepfour", index="0") == \
        NodeStatus.SUCCESS

    assert gcd_nop_project.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SUCCESS
    assert gcd_nop_project.history("job0").get("record", "status", step="stepthree", index="0") == \
        NodeStatus.SUCCESS
    assert gcd_nop_project.history("job0").get("record", "status", step="stepfour", index="0") == \
        NodeStatus.SUCCESS


def test_resume_value_changed(gcd_nop_project):
    EditableSchema(gcd_nop_project).insert("option", "testing", Parameter("str"))

    assert gcd_nop_project.run()
    run_copy = gcd_nop_project.copy()
    time.sleep(1)  # delay to ensure timestamps differ

    # Change require list
    assert gcd_nop_project.set("tool", "builtin", "task", "nop", "require", "option,testing",
                               step="stepthree", index="0")
    assert gcd_nop_project.set("option", "testing", "thistest")
    gcd_nop_project.logger.setLevel(logging.DEBUG)
    assert gcd_nop_project.run()

    assert run_copy.history("job0").get("record", "endtime", step="steptwo", index="0") == \
        gcd_nop_project.history("job0").get("record", "endtime", step="steptwo", index="0")

    assert run_copy.history("job0").get("record", "endtime", step="stepthree", index="0") != \
        gcd_nop_project.history("job0").get("record", "endtime", step="stepthree", index="0")

    assert run_copy.history("job0").get("record", "endtime", step="stepfour", index="0") != \
        gcd_nop_project.history("job0").get("record", "endtime", step="stepfour", index="0")

    assert run_copy.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SUCCESS
    assert run_copy.history("job0").get("record", "status", step="stepthree", index="0") == \
        NodeStatus.SUCCESS
    assert run_copy.history("job0").get("record", "status", step="stepfour", index="0") == \
        NodeStatus.SUCCESS

    assert gcd_nop_project.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SUCCESS
    assert gcd_nop_project.history("job0").get("record", "status", step="stepthree", index="0") == \
        NodeStatus.SUCCESS
    assert gcd_nop_project.history("job0").get("record", "status", step="stepfour", index="0") == \
        NodeStatus.SUCCESS