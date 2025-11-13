import logging
import os
import pytest
import time

import os.path

from unittest.mock import patch

from siliconcompiler import Project, Flowgraph, Design, NodeStatus
from siliconcompiler.scheduler import Scheduler, SCRuntimeError
from siliconcompiler.schema import EditableSchema, Parameter

from siliconcompiler.tools.builtin.nop import NOPTask
from siliconcompiler.utils.paths import jobdir
from siliconcompiler.tool import TaskExecutableNotReceived, TaskSkip, Task


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


class DummyTask(Task):
    def __init__(self):
        super().__init__()
        self.add_parameter("check", "str", "dummy require")

    def tool(self) -> str:
        return "testtool"

    def task(self) -> str:
        return "dummy"

    def setup(self):
        self.add_required_key("var", "check")

    def run(self):
        return 0


class SelectiveSkip(Task):
    def __init__(self):
        super().__init__()
        self.add_parameter("skip", "bool", "skip this")

    def tool(self) -> str:
        return "testtool"

    def task(self) -> str:
        return "skippable"

    def run(self):
        return 0

    def pre_process(self) -> None:
        super().pre_process()
        if self.get("var", "skip"):
            raise TaskSkip("skipped")


class SetupSkip(Task):
    def __init__(self):
        super().__init__()

    def tool(self) -> str:
        return "testtool"

    def task(self) -> str:
        return "skippable"

    def run(self):
        return 1

    def setup(self) -> None:
        raise TaskSkip("skipped")


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
    with pytest.raises(SCRuntimeError, match=r"^flow must be specified$"):
        Scheduler(Project(Design("testdesign")))


def test_init_flow_not_defined(basic_project):
    basic_project.set("option", "flow", "testflow")
    with pytest.raises(SCRuntimeError, match=r"^flow is not defined$"):
        Scheduler(basic_project)


def test_init_flow_not_valid(basic_project):
    with patch("siliconcompiler.flowgraph.Flowgraph.validate") as call:
        call.return_value = False
        with pytest.raises(SCRuntimeError,
                           match=r"^test flowgraph contains errors and cannot be run\.$"):
            Scheduler(basic_project)


def test_init_flow_runtime_not_valid(basic_project):
    with patch("siliconcompiler.flowgraph.Flowgraph.validate") as call0, \
         patch("siliconcompiler.flowgraph.RuntimeFlowgraph.validate") as call1:
        call0.return_value = True
        call1.return_value = False
        with pytest.raises(SCRuntimeError,
                           match=r"^test flowgraph contains errors and cannot be run\.$"):
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
    os.makedirs(os.path.join(jobdir(basic_project), "sc_keep_this"), exist_ok=True)
    with open(os.path.join(jobdir(basic_project), "job.log"), "w") as f:
        f.write("test")

    with patch("shutil.rmtree", autospec=True) as rmtree, \
            patch("os.remove") as remove:
        scheduler._Scheduler__clean_build_dir_full()
        assert rmtree.call_count == 2
        rmtree.assert_any_call(os.path.join(jobdir(basic_project), "rmthis"))
        rmtree.assert_any_call(os.path.join(jobdir(basic_project), "sc_keep_this"))
        remove.assert_called_once()


def test_clean_build_dir_full_keep_log(basic_project):
    basic_project.set('option', 'clean', True)

    scheduler = Scheduler(basic_project)

    os.makedirs(jobdir(basic_project), exist_ok=True)
    os.makedirs(os.path.join(jobdir(basic_project), "rmthis"), exist_ok=True)
    os.makedirs(os.path.join(jobdir(basic_project), "sc_keep_this"), exist_ok=True)
    with open(os.path.join(jobdir(basic_project), "job.log"), "w") as f:
        f.write("test")

    with patch("shutil.rmtree", autospec=True) as rmtree, \
            patch("os.remove") as remove:
        scheduler._Scheduler__clean_build_dir_full(recheck=True)
        rmtree.assert_called_once_with(os.path.join(jobdir(basic_project), "rmthis"))
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
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.scheduler.Scheduler.check_manifest",
               autospec=True) as call:
        call.return_value = True
        scheduler.run()
        call.assert_called_once()


def test_check_manifest_fail(basic_project):
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.scheduler.Scheduler.check_manifest",
               autospec=True) as check_manifest, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__run_setup") as run_setup, \
            patch("siliconcompiler.scheduler.Scheduler.configure_nodes") as configure_nodes, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_tool_versions") \
            as check_tool_versions, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_tool_requirements") \
            as check_tool_requirements, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__clean_build_dir_incr") \
            as clean_build_dir_incr, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_flowgraph_io") \
            as check_flowgraph_io:
        check_manifest.return_value = False
        with pytest.raises(RuntimeError, match=r'^check_manifest\(\) failed$'):
            scheduler.run()
        check_manifest.assert_called_once()
        run_setup.assert_not_called()
        configure_nodes.assert_not_called()
        check_tool_versions.assert_not_called()
        check_tool_requirements.assert_not_called()
        clean_build_dir_incr.assert_not_called()
        check_flowgraph_io.assert_not_called()


def test_flowgraphio_fail(basic_project):
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.scheduler.Scheduler.check_manifest",
               autospec=True) as check_manifest, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__run_setup") as run_setup, \
            patch("siliconcompiler.scheduler.Scheduler.configure_nodes") as configure_nodes, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_tool_versions") \
            as check_tool_versions, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_tool_requirements") \
            as check_tool_requirements, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__clean_build_dir_incr") \
            as clean_build_dir_incr, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_flowgraph_io") \
            as check_flowgraph_io:
        check_manifest.return_value = True
        check_tool_versions.return_value = True
        check_tool_requirements.return_value = True
        check_flowgraph_io.return_value = False
        with pytest.raises(RuntimeError, match=r'^Flowgraph file IO constrains errors$'):
            scheduler.run()
        check_manifest.assert_called_once()
        run_setup.assert_called_once()
        configure_nodes.assert_called_once()
        check_tool_versions.assert_called_once()
        check_tool_requirements.assert_called_once()
        clean_build_dir_incr.assert_called_once()
        check_flowgraph_io.assert_called_once()


def test_toolversion_fail(basic_project):
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.scheduler.Scheduler.check_manifest",
               autospec=True) as check_manifest, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__run_setup") as run_setup, \
            patch("siliconcompiler.scheduler.Scheduler.configure_nodes") as configure_nodes, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_tool_versions") \
            as check_tool_versions, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_tool_requirements") \
            as check_tool_requirements, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__clean_build_dir_incr") \
            as clean_build_dir_incr, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_flowgraph_io") \
            as check_flowgraph_io:
        check_manifest.return_value = True
        check_tool_versions.return_value = False
        with pytest.raises(RuntimeError, match=r'^Tools did not meet version requirements$'):
            scheduler.run()
        check_manifest.assert_called_once()
        run_setup.assert_called_once()
        configure_nodes.assert_called_once()
        check_tool_versions.assert_called_once()
        check_tool_requirements.assert_not_called()
        clean_build_dir_incr.assert_not_called()
        check_flowgraph_io.assert_not_called()


def test_toolrequirement_fail(basic_project):
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.scheduler.Scheduler.check_manifest",
               autospec=True) as check_manifest, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__run_setup") as run_setup, \
            patch("siliconcompiler.scheduler.Scheduler.configure_nodes") as configure_nodes, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_tool_versions") \
            as check_tool_versions, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_tool_requirements") \
            as check_tool_requirements, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__clean_build_dir_incr") \
            as clean_build_dir_incr, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_flowgraph_io") \
            as check_flowgraph_io:
        check_manifest.return_value = True
        check_tool_versions.return_value = True
        check_tool_requirements.return_value = False
        with pytest.raises(RuntimeError, match=r'^Tools requirements not met$'):
            scheduler.run()
        check_manifest.assert_called_once()
        run_setup.assert_called_once()
        configure_nodes.assert_called_once()
        check_tool_versions.assert_called_once()
        check_tool_requirements.assert_called_once()
        clean_build_dir_incr.assert_not_called()
        check_flowgraph_io.assert_not_called()


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

    nop = NOPTask.find_task(basic_project_no_flow)
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

    nop = NOPTask.find_task(basic_project_no_flow)
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

    nop = NOPTask.find_task(basic_project_no_flow)
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

    nop = NOPTask.find_task(basic_project_no_flow)
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

    nop = NOPTask.find_task(basic_project_no_flow)
    nop.add_output_file("test.v", step="stepone", index="0")
    nop.add_output_file("test.v", step="stepone", index="1")
    nop.add_input_file("test.v", step="steptwo", index="0")

    assert scheduler._Scheduler__check_flowgraph_io() is False
    assert "Invalid flow: steptwo/0 receives test.v from multiple input tasks" in caplog.text


@pytest.mark.timeout(60)
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


@pytest.mark.timeout(60)
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


@pytest.mark.timeout(60)
def test_resume_afterskipped(gcd_design):
    project = Project(gcd_design)
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    flow = Flowgraph("skipflow")
    flow.node("stepone", DummyTask())
    flow.node("steptwo", SelectiveSkip())
    flow.node("stepthree", DummyTask())
    flow.node("stepfour", DummyTask())
    flow.edge("stepone", "steptwo")
    flow.edge("steptwo", "stepthree")
    flow.edge("stepthree", "stepfour")
    project.set_flow(flow)

    SelectiveSkip.find_task(project).set("var", "skip", True)
    DummyTask.find_task(project).set("var", "check", "this")

    assert project.run()
    assert project.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SKIPPED
    assert project.history("job0").get("record", "toolexitcode", step="steptwo", index="0") is None
    starttime = project.history("job0").get("record", "starttime", step="stepthree", index="0")

    time.sleep(1)  # delay to ensure timestamps differ
    SelectiveSkip.find_task(project).set("var", "skip", False)
    DummyTask.find_task(project).set("var", "check", "this")
    DummyTask.find_task(project).set("var", "check", "that", step="stepone")

    assert project.run()
    assert project.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SUCCESS
    assert project.history("job0").get("record", "toolexitcode", step="steptwo", index="0") == 0
    assert starttime != project.history("job0").get("record", "starttime",
                                                    step="stepthree", index="0")


@pytest.mark.timeout(60)
def test_resume_afterskipped_at_setup(gcd_design):
    project = Project(gcd_design)
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    flow = Flowgraph("skipflow")
    flow.node("stepone", DummyTask())
    flow.node("steptwo", SetupSkip())
    flow.node("stepthree", DummyTask())
    flow.node("stepfour", DummyTask())
    flow.edge("stepone", "steptwo")
    flow.edge("steptwo", "stepthree")
    flow.edge("stepthree", "stepfour")
    project.set_flow(flow)

    DummyTask.find_task(project).set("var", "check", "this")

    assert project.run()
    assert project.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SKIPPED
    assert project.history("job0").get("record", "toolexitcode", step="steptwo", index="0") is None
    starttime = project.history("job0").get("record", "starttime", step="stepthree", index="0")

    time.sleep(1)  # delay to ensure timestamps differ
    DummyTask.find_task(project).set("var", "check", "this")
    DummyTask.find_task(project).set("var", "check", "that", step="stepone")

    assert project.run()
    assert project.history("job0").get("record", "status", step="steptwo", index="0") == \
        NodeStatus.SKIPPED
    assert project.history("job0").get("record", "toolexitcode", step="steptwo", index="0") is None
    assert starttime != project.history("job0").get("record", "starttime",
                                                    step="stepthree", index="0")


@pytest.mark.timeout(60)
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


def test_check_tool_requirements_local(gcd_nop_project, monkeypatch, caplog):
    monkeypatch.setattr(gcd_nop_project, "_Project__logger", logging.getLogger())
    gcd_nop_project.logger.setLevel(logging.INFO)

    EditableSchema(gcd_nop_project).insert("option", "testing", Parameter("str"))
    EditableSchema(gcd_nop_project).insert("option", "testing_file", Parameter("file"))
    assert gcd_nop_project.set("option", "testing_file", "thistest.txt")

    # Change set requirement
    # Add unset key
    assert gcd_nop_project.set("tool", "builtin", "task", "nop", "require", "option,testing",
                               step="stepthree", index="0")
    # Add invalid key
    assert gcd_nop_project.add("tool", "builtin", "task", "nop", "require", "option1,testing",
                               step="stepthree", index="0")
    # Add missing file
    assert gcd_nop_project.add("tool", "builtin", "task", "nop", "require", "option,testing_file",
                               step="stepthree", index="0")
    assert Scheduler(gcd_nop_project)._Scheduler__check_tool_requirements() is False

    assert "No value set for required keypath [option,testing] for stepthree/0." in caplog.text
    assert "Cannot resolve required keypath [option1,testing] for stepthree/0." in caplog.text
    assert "Cannot resolve path thistest.txt in required file keypath [option,testing_file] " \
        "for stepthree/0." in caplog.text


def test_check_tool_requirements_remote(gcd_nop_project, monkeypatch, caplog):
    monkeypatch.setattr(gcd_nop_project, "_Project__logger", logging.getLogger())
    gcd_nop_project.logger.setLevel(logging.INFO)

    EditableSchema(gcd_nop_project).insert("option", "testing", Parameter("str"))
    EditableSchema(gcd_nop_project).insert("option", "testing_file", Parameter("file"))
    assert gcd_nop_project.set("option", "testing_file", "thistest.txt")
    gcd_nop_project.option.set_remote(True)

    # Change set requirement
    # Add unset key
    assert gcd_nop_project.set("tool", "builtin", "task", "nop", "require", "option,testing",
                               step="stepthree", index="0")
    # Add invalid key
    assert gcd_nop_project.add("tool", "builtin", "task", "nop", "require", "option1,testing",
                               step="stepthree", index="0")
    # Add missing file
    assert gcd_nop_project.add("tool", "builtin", "task", "nop", "require", "option,testing_file",
                               step="stepthree", index="0")
    assert Scheduler(gcd_nop_project)._Scheduler__check_tool_requirements() is False

    assert "No value set for required keypath [option,testing] for stepthree/0." in caplog.text
    assert "Cannot resolve required keypath [option1,testing] for stepthree/0." in caplog.text
    assert "Cannot resolve path thistest.txt in required file keypath [option,testing_file] " \
        "for stepthree/0." not in caplog.text


@pytest.mark.parametrize("scheduler", ("docker", "slurm"))
def test_check_tool_requirements_non_local(gcd_nop_project, monkeypatch, caplog, scheduler):
    monkeypatch.setattr(gcd_nop_project, "_Project__logger", logging.getLogger())
    gcd_nop_project.logger.setLevel(logging.INFO)

    EditableSchema(gcd_nop_project).insert("option", "testing", Parameter("str"))
    EditableSchema(gcd_nop_project).insert("option", "testing_file", Parameter("file"))
    assert gcd_nop_project.set("option", "testing_file", "thistest.txt")
    gcd_nop_project.option.scheduler.set_name(scheduler)

    # Change set requirement
    # Add unset key
    assert gcd_nop_project.set("tool", "builtin", "task", "nop", "require", "option,testing",
                               step="stepthree", index="0")
    # Add invalid key
    assert gcd_nop_project.add("tool", "builtin", "task", "nop", "require", "option1,testing",
                               step="stepthree", index="0")
    # Add missing file
    assert gcd_nop_project.add("tool", "builtin", "task", "nop", "require", "option,testing_file",
                               step="stepthree", index="0")
    assert Scheduler(gcd_nop_project)._Scheduler__check_tool_requirements() is False

    assert "No value set for required keypath [option,testing] for stepthree/0." in caplog.text
    assert "Cannot resolve required keypath [option1,testing] for stepthree/0." in caplog.text
    assert "Cannot resolve path thistest.txt in required file keypath [option,testing_file] " \
        "for stepthree/0." not in caplog.text


def test_check_tool_requirements_pass(gcd_nop_project, monkeypatch, caplog):
    monkeypatch.setattr(gcd_nop_project, "_Project__logger", logging.getLogger())
    gcd_nop_project.logger.setLevel(logging.INFO)

    EditableSchema(gcd_nop_project).insert("option", "testing", Parameter("str"))
    assert gcd_nop_project.set("option", "testing", "thistest")

    # Change set requirement
    assert gcd_nop_project.set("tool", "builtin", "task", "nop", "require", "option,testing",
                               step="stepthree", index="0")
    assert Scheduler(gcd_nop_project)._Scheduler__check_tool_requirements() is True

    assert caplog.text == ""


def test_install_file_logger(basic_project):
    """Test that __install_file_logger creates job.log and handles backup files."""
    scheduler = Scheduler(basic_project)

    # Create job directory
    os.makedirs(jobdir(basic_project), exist_ok=True)

    # Create existing job.log
    existing_log = os.path.join(jobdir(basic_project), "job.log")
    with open(existing_log, "w") as f:
        f.write("existing log content")

    # Call __install_file_logger
    scheduler._Scheduler__install_file_logger()

    # Check that new log exists
    assert os.path.exists(existing_log)

    # Check that backup was created
    backup_log = os.path.join(jobdir(basic_project), "job.log.bak")
    assert os.path.exists(backup_log)

    # Check backup content
    with open(backup_log, "r") as f:
        assert f.read() == "existing log content"


@pytest.mark.timeout(90)
def test_install_file_logger_multiple_backups(basic_project):
    """Test that __install_file_logger handles multiple backup files."""
    scheduler = Scheduler(basic_project)

    # Create job directory
    os.makedirs(jobdir(basic_project), exist_ok=True)

    # Create existing job.log and backups
    existing_log = os.path.join(jobdir(basic_project), "job.log")
    with open(existing_log, "w") as f:
        f.write("log 1")

    backup1 = os.path.join(jobdir(basic_project), "job.log.bak")
    with open(backup1, "w") as f:
        f.write("backup 1")

    backup2 = os.path.join(jobdir(basic_project), "job.log.bak.1")
    with open(backup2, "w") as f:
        f.write("backup 2")

    # Call __install_file_logger
    scheduler._Scheduler__install_file_logger()

    # Check that new backup was created with correct number
    backup3 = os.path.join(jobdir(basic_project), "job.log.bak.2")
    assert os.path.exists(backup3)
    with open(backup3, "r") as f:
        assert f.read() == "log 1"


@pytest.mark.timeout(90)
def test_install_file_logger_no_existing_log(basic_project):
    """Test that __install_file_logger works when no existing log file."""
    scheduler = Scheduler(basic_project)

    # Create job directory
    os.makedirs(jobdir(basic_project), exist_ok=True)

    # Call __install_file_logger
    scheduler._Scheduler__install_file_logger()

    # Check that new log exists
    existing_log = os.path.join(jobdir(basic_project), "job.log")
    assert os.path.exists(existing_log)

    # Check that no backup was created
    backup_log = os.path.join(jobdir(basic_project), "job.log.bak")
    assert not os.path.exists(backup_log)


def test_logfile_init(basic_project):
    assert Scheduler(basic_project).log is None


def test_logfile_post_install(basic_project):
    scheduler = Scheduler(basic_project)

    # Create job directory
    os.makedirs(jobdir(basic_project), exist_ok=True)

    assert scheduler.log is None
    # Call __install_file_logger
    scheduler._Scheduler__install_file_logger()

    assert scheduler.log == os.path.join(jobdir(basic_project), "job.log")


def test_check_tool_versions_local_pass(gcd_nop_project, monkeypatch, caplog):
    monkeypatch.setattr(gcd_nop_project, "_Project__logger", logging.getLogger())
    gcd_nop_project.logger.setLevel(logging.INFO)

    assert gcd_nop_project.set("tool", "builtin", "task", "nop", "exe", "this.exe")

    with patch("siliconcompiler.scheduler.SchedulerNode.get_exe_path") as get_exe_path, \
            patch("siliconcompiler.scheduler.SchedulerNode.check_version") as check_version:
        get_exe_path.return_value = "exe"
        check_version.return_value = ("version", True)
        assert Scheduler(gcd_nop_project)._Scheduler__check_tool_versions() is True
        assert get_exe_path.call_count == 4
        assert check_version.call_count == 4

    assert caplog.text == ""


def test_check_tool_versions_local_pass_not_received(gcd_nop_project, monkeypatch, caplog):
    monkeypatch.setattr(gcd_nop_project, "_Project__logger", logging.getLogger())
    gcd_nop_project.logger.setLevel(logging.INFO)

    assert gcd_nop_project.set("tool", "builtin", "task", "nop", "exe", "this.exe")

    def fail(*args, **kwargs):
        raise TaskExecutableNotReceived()

    with patch("siliconcompiler.scheduler.SchedulerNode.get_exe_path") as get_exe_path, \
            patch("siliconcompiler.scheduler.SchedulerNode.check_version") as check_version:
        get_exe_path.side_effect = fail
        assert Scheduler(gcd_nop_project)._Scheduler__check_tool_versions() is True
        assert get_exe_path.call_count == 4
        check_version.assert_not_called()

    assert caplog.text == ""


def test_check_tool_versions_remote(gcd_nop_project, monkeypatch, caplog):
    monkeypatch.setattr(gcd_nop_project, "_Project__logger", logging.getLogger())
    gcd_nop_project.logger.setLevel(logging.INFO)

    gcd_nop_project.option.set_remote(True)

    assert gcd_nop_project.set("tool", "builtin", "task", "nop", "exe", "this.exe")

    with patch("siliconcompiler.scheduler.SchedulerNode.get_exe_path") as get_exe_path, \
            patch("siliconcompiler.scheduler.SchedulerNode.check_version") as check_version:
        assert Scheduler(gcd_nop_project)._Scheduler__check_tool_versions() is True
        get_exe_path.assert_not_called()
        check_version.assert_not_called()

    assert caplog.text == ""


def test_check_tool_versions_local_fail(gcd_nop_project, monkeypatch, caplog):
    monkeypatch.setattr(gcd_nop_project, "_Project__logger", logging.getLogger())
    gcd_nop_project.logger.setLevel(logging.INFO)

    assert gcd_nop_project.set("tool", "builtin", "task", "nop", "exe", "this.exe")

    with patch("siliconcompiler.scheduler.SchedulerNode.get_exe_path") as get_exe_path, \
            patch("siliconcompiler.scheduler.SchedulerNode.check_version") as check_version:
        get_exe_path.return_value = "exe"
        check_version.return_value = ("version", False)
        assert Scheduler(gcd_nop_project)._Scheduler__check_tool_versions() is False
        assert get_exe_path.call_count == 4
        assert check_version.call_count == 4

    assert "Executable for stepfour/0 did not meet version checks" in caplog.text
    assert "Executable for stepone/0 did not meet version checks" in caplog.text
    assert "Executable for steptwo/0 did not meet version checks" in caplog.text
    assert "Executable for stepthree/0 did not meet version checks" in caplog.text


@pytest.mark.parametrize("scheduler", ("docker", "slurm"))
def test_check_tool_versions_non_local_fail(gcd_nop_project, monkeypatch, caplog, scheduler):
    monkeypatch.setattr(gcd_nop_project, "_Project__logger", logging.getLogger())
    gcd_nop_project.logger.setLevel(logging.INFO)

    assert gcd_nop_project.set("tool", "builtin", "task", "nop", "exe", "this.exe")
    gcd_nop_project.option.scheduler.set_name(scheduler, step="stepone")
    gcd_nop_project.option.scheduler.set_name(scheduler, step="stepthree")

    with patch("siliconcompiler.scheduler.SchedulerNode.get_exe_path") as get_exe_path, \
            patch("siliconcompiler.scheduler.SchedulerNode.check_version") as check_version:
        get_exe_path.return_value = "exe"
        check_version.return_value = ("version", False)
        assert Scheduler(gcd_nop_project)._Scheduler__check_tool_versions() is False
        assert get_exe_path.call_count == 2
        assert check_version.call_count == 2

    assert "Executable for stepfour/0 did not meet version checks" in caplog.text
    assert "Executable for steptwo/0 did not meet version checks" in caplog.text


@pytest.mark.parametrize("scheduler", ("docker", "slurm"))
def test_check_tool_versions_non_local_pass(gcd_nop_project, monkeypatch, caplog, scheduler):
    monkeypatch.setattr(gcd_nop_project, "_Project__logger", logging.getLogger())
    gcd_nop_project.logger.setLevel(logging.INFO)

    assert gcd_nop_project.set("tool", "builtin", "task", "nop", "exe", "this.exe")
    gcd_nop_project.option.scheduler.set_name(scheduler, step="stepone")
    gcd_nop_project.option.scheduler.set_name(scheduler, step="stepthree")

    with patch("siliconcompiler.scheduler.SchedulerNode.get_exe_path") as get_exe_path, \
            patch("siliconcompiler.scheduler.SchedulerNode.check_version") as check_version:
        get_exe_path.return_value = "exe"
        check_version.return_value = ("version", True)
        assert Scheduler(gcd_nop_project)._Scheduler__check_tool_versions() is True
        assert get_exe_path.call_count == 2
        assert check_version.call_count == 2

    assert caplog.text == ""


def test_manifest_path(basic_project):
    assert Scheduler(basic_project).manifest == os.path.abspath(os.path.join(
        "build", "testdesign", "job0", "testdesign.pkg.json"
    ))


def test_logger(basic_project):
    assert Scheduler(basic_project)._Scheduler__logger is not basic_project.logger
