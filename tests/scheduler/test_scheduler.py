import logging
import os
import pytest
import subprocess
import sys
import textwrap
import time

import os.path

from pathlib import Path

from unittest.mock import patch, MagicMock

from siliconcompiler import Project, Flowgraph, Design, NodeStatus
from siliconcompiler.scheduler import Scheduler, SCRuntimeError, SchedulerNode, \
    SlurmSchedulerNode, DockerSchedulerNode
from siliconcompiler.schema import EditableSchema, Parameter

from siliconcompiler.tools.builtin.nop import NOPTask
from siliconcompiler.tools.builtin.join import JoinTask
from siliconcompiler.utils.paths import jobdir
from siliconcompiler.tool import TaskExecutableNotReceived, TaskSkip, Task
from siliconcompiler.utils.multiprocessing import MPManager


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


class DupInputTask(Task):
    def tool(self) -> str:
        return "testtool"

    def task(self) -> str:
        return "dupinput"

    def run(self):
        return 0


class SeedTask(Task):
    """Entry task that writes a seed.v file so downstream NOPTasks have
    something to propagate."""

    def tool(self) -> str:
        return "seedtool"

    def task(self) -> str:
        return "seed"

    def setup(self):
        self.add_output_file("seed.v")

    def run(self):
        with open("outputs/seed.v", "w") as f:
            f.write("// seed\n")
        return 0


@pytest.fixture
def forkjoin_project(gcd_design):
    """A fork/join flow used to exercise option.from after a fork:

        entry --> A1 --> A2 --> joinstep
              \\-> B1 --> B2 -/
    """
    project = Project(gcd_design)
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    flow = Flowgraph("forkjoin")
    flow.node("entry", SeedTask())
    flow.node("A1", NOPTask())
    flow.node("A2", NOPTask())
    flow.node("B1", NOPTask())
    flow.node("B2", NOPTask())
    flow.node("joinstep", NOPTask())

    flow.edge("entry", "A1")
    flow.edge("A1", "A2")
    flow.edge("entry", "B1")
    flow.edge("B1", "B2")
    flow.edge("A2", "joinstep")
    flow.edge("B2", "joinstep")

    project.set_flow(flow)
    return project


class AdditionalFiles(Task):
    def __init__(self):
        super().__init__()
        self.add_parameter("files", "[file]", "extra files")
        self.add_parameter("dirs", "[dir]", "extra directories")

    def tool(self) -> str:
        return "testtool"

    def task(self) -> str:
        return "additional_files"

    def setup(self):
        if self.get("var", "files"):
            self.add_required_key("var", "files")
        if self.get("var", "dirs"):
            self.add_required_key("var", "dirs")

    def run(self):
        return 0


@pytest.fixture
def gcd_additional_files_project(gcd_design):
    project = Project(gcd_design)
    project.add_fileset("rtl")
    project.add_fileset("sdc")

    flow = Flowgraph("collectflow")
    flow.node("node1", AdditionalFiles())
    flow.node("node2", AdditionalFiles())
    flow.edge("node1", "node2")
    project.set_flow(flow)

    dir1 = Path("node1_dir")
    dir1.mkdir(exist_ok=True)

    file1 = Path("node1_file")
    file1.write_text("// file1 content")

    AdditionalFiles.find_task(project).set("var", "files", [str(file1)], step="node1")
    AdditionalFiles.find_task(project).set("var", "dirs", [str(dir1)], step="node1")

    dir1 = Path("node2_dir")
    dir1.mkdir(exist_ok=True)

    file1 = Path("node2_file")
    file1.write_text("// file1 content")
    AdditionalFiles.find_task(project).set("var", "files", [str(file1)], step="node2")
    AdditionalFiles.find_task(project).set("var", "dirs", [str(dir1)], step="node2")

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


def test_init_node_cls_local(basic_project):
    # No scheduler set, so the local node class is used
    scheduler = Scheduler(basic_project)
    assert type(scheduler._Scheduler__tasks[("stepone", "0")]) is SchedulerNode


@pytest.mark.parametrize("scheduler_name,node_cls", [
    ("slurm", SlurmSchedulerNode),
    ("docker", DockerSchedulerNode)])
def test_init_node_cls(basic_project, scheduler_name, node_cls):
    basic_project.option.scheduler.set_name(scheduler_name)

    scheduler = Scheduler(basic_project)
    assert type(scheduler._Scheduler__tasks[("stepone", "0")]) is node_cls


@pytest.mark.parametrize("scheduler_name", ("lsf", "sge"))
def test_init_node_cls_not_implemented(basic_project, scheduler_name):
    basic_project.option.scheduler.set_name(scheduler_name)

    with pytest.raises(SCRuntimeError,
                       match=rf"^Unsupported scheduler '{scheduler_name}' for node stepone/0$"):
        Scheduler(basic_project)


@pytest.mark.parametrize("scheduler_name,node_cls", [
    ("slurm", SlurmSchedulerNode),
    ("docker", DockerSchedulerNode)])
def test_init_node_cls_per_node(gcd_nop_project, scheduler_name, node_cls):
    # Only some nodes are scheduled, the rest fall back to local execution
    gcd_nop_project.option.scheduler.set_name(scheduler_name, step="stepone")
    gcd_nop_project.option.scheduler.set_name(scheduler_name, step="stepthree")

    tasks = Scheduler(gcd_nop_project)._Scheduler__tasks
    assert type(tasks[("stepone", "0")]) is node_cls
    assert type(tasks[("steptwo", "0")]) is SchedulerNode
    assert type(tasks[("stepthree", "0")]) is node_cls
    assert type(tasks[("stepfour", "0")]) is SchedulerNode


@pytest.mark.parametrize("scheduler_name", ("lsf", "sge"))
def test_init_node_cls_per_node_not_implemented(gcd_nop_project, scheduler_name):
    gcd_nop_project.option.scheduler.set_name(scheduler_name, step="stepthree")

    with pytest.raises(SCRuntimeError,
                       match=rf"^Unsupported scheduler '{scheduler_name}' for node stepthree/0$"):
        Scheduler(gcd_nop_project)


def test_check_display_run(basic_project):
    # Checks if check_display() is called during run()
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_display",
               autospec=True) as call:
        scheduler.run()
        call.assert_called_once()


@patch('sys.platform', 'linux')
def test_check_display_nodisplay(project_logger, basic_project, remove_display_environment, caplog):
    # Checks if the nodisplay option is set
    # On linux system without display
    project_logger(basic_project)
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
    assert scheduler._Scheduler__tasks[("stepone", "0")].jobname == "job1"


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
    with open(os.path.join(jobdir(basic_project), "job.20260101-100000.log"), "w") as f:
        f.write("test")

    with patch("shutil.rmtree", autospec=True) as rmtree, \
            patch("os.remove") as remove:
        scheduler._Scheduler__clean_build_dir_full(recheck=True)
        rmtree.assert_called_once()
        remove.assert_called_once_with(os.path.join(jobdir(basic_project),
                                                    "job.20260101-100000.log"))


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


def test_check_manifest_checks_project_directly(basic_project):
    # _init_run() has already run on the project, so the checks must not
    # resolve and check a copy again
    scheduler = Scheduler(basic_project)
    with patch("siliconcompiler.Project._check_manifest", autospec=True) as check, \
            patch("siliconcompiler.Project.check_manifest", autospec=True) as public_check:
        check.return_value = True
        assert scheduler.check_manifest() is True
        check.assert_called_once_with(basic_project)
        public_check.assert_not_called()


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
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_task_classes") \
            as check_task_classes, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_flowgraph_io") \
            as check_flowgraph_io:
        check_manifest.return_value = False
        with pytest.raises(RuntimeError, match=r'^check_manifest\(\) failed$'):
            scheduler.run()
        check_manifest.assert_called_once()
        run_setup.assert_not_called()
        configure_nodes.assert_not_called()
        check_task_classes.assert_not_called()
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
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_task_classes") \
            as check_task_classes, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_flowgraph_io") \
            as check_flowgraph_io:
        check_manifest.return_value = True
        check_task_classes.return_value = True
        check_tool_versions.return_value = True
        check_tool_requirements.return_value = True
        check_flowgraph_io.return_value = False
        with pytest.raises(RuntimeError, match=r'^Flowgraph file IO constrains errors$'):
            scheduler.run()
        check_manifest.assert_called_once()
        run_setup.assert_called_once()
        configure_nodes.assert_called_once()
        check_task_classes.assert_called_once()
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
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_task_classes") \
            as check_task_classes, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_flowgraph_io") \
            as check_flowgraph_io:
        check_manifest.return_value = True
        check_task_classes.return_value = True
        check_tool_versions.return_value = False
        with pytest.raises(RuntimeError, match=r'^Tools did not meet version requirements$'):
            scheduler.run()
        check_manifest.assert_called_once()
        run_setup.assert_called_once()
        configure_nodes.assert_called_once()
        check_task_classes.assert_called_once()
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
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_task_classes") \
            as check_task_classes, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_flowgraph_io") \
            as check_flowgraph_io:
        check_manifest.return_value = True
        check_task_classes.return_value = True
        check_tool_versions.return_value = True
        check_tool_requirements.return_value = False
        with pytest.raises(RuntimeError, match=r'^Tools requirements not met$'):
            scheduler.run()
        check_manifest.assert_called_once()
        run_setup.assert_called_once()
        configure_nodes.assert_called_once()
        check_task_classes.assert_called_once()
        check_tool_versions.assert_called_once()
        check_tool_requirements.assert_called_once()
        clean_build_dir_incr.assert_not_called()
        check_flowgraph_io.assert_not_called()


def test_classcheck_fail(basic_project):
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
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_task_classes") \
            as check_task_classes, \
            patch("siliconcompiler.scheduler.Scheduler._Scheduler__check_flowgraph_io") \
            as check_flowgraph_io:
        check_manifest.return_value = True
        check_task_classes.return_value = False
        with pytest.raises(RuntimeError, match=r'^Task classes are missing$'):
            scheduler.run()
        check_manifest.assert_called_once()
        run_setup.assert_called_once()
        configure_nodes.assert_called_once()
        check_task_classes.assert_called_once()
        check_tool_versions.assert_not_called()
        check_tool_requirements.assert_not_called()
        clean_build_dir_incr.assert_not_called()
        check_flowgraph_io.assert_not_called()


def test_check_task_classes_fail(project_logger, basic_project, caplog):
    project_logger(basic_project)
    basic_project.logger.setLevel(logging.INFO)

    EditableSchema(basic_project).insert("tool", "builtin", "task", "nop", Task(), clobber=True)

    scheduler = Scheduler(basic_project)

    assert scheduler._Scheduler__check_task_classes() is False
    assert "Invalid task: stepone/0 did not load the correct class module" in caplog.text


def test_check_task_classes_pass(project_logger, basic_project, caplog):
    project_logger(basic_project)
    basic_project.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project)

    assert scheduler._Scheduler__check_task_classes() is True
    assert caplog.text == ""


def test_check_flowgraph_io_basic(project_logger, basic_project, caplog):
    """Smoke integration test that the scheduler still walks nodes and reports
    success when there are no IO requirements. Detailed validation behavior
    lives with Task._validate_io and is tested in tests/test_tool.py and
    tests/tools/test_builtin.py."""
    project_logger(basic_project)
    basic_project.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project)

    assert scheduler._Scheduler__check_flowgraph_io() is True
    assert caplog.text == ""


def test_check_flowgraph_io_propagates_failure(project_logger, basic_project_no_flow, caplog):
    """Scheduler-level smoke: a failing _validate_io result is surfaced."""
    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    basic_project_no_flow.set_flow(flow)

    project_logger(basic_project_no_flow)
    basic_project_no_flow.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project_no_flow)

    nop = NOPTask.find_task(basic_project_no_flow)
    nop.add_input_file("missing.v", step="steptwo", index="0")

    assert scheduler._Scheduler__check_flowgraph_io() is False
    assert "Invalid flow: steptwo/0 will not receive required input missing.v" in caplog.text


def test_check_flowgraph_io_rejects_duplicate_input(project_logger, basic_project_no_flow,
                                                    caplog):
    """Non-builtin task with ambiguous fan-in (same input name from two
    upstreams) must fail validation at the scheduler entrypoint."""
    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask(), index=0)
    flow.node("stepone", NOPTask(), index=1)
    flow.node("steptwo", DupInputTask())
    flow.edge("stepone", "steptwo", tail_index=0)
    flow.edge("stepone", "steptwo", tail_index=1)
    basic_project_no_flow.set_flow(flow)

    project_logger(basic_project_no_flow)
    basic_project_no_flow.logger.setLevel(logging.INFO)

    scheduler = Scheduler(basic_project_no_flow)

    NOPTask.find_task(basic_project_no_flow).add_output_file(
        "test.v", step="stepone", index="0")
    NOPTask.find_task(basic_project_no_flow).add_output_file(
        "test.v", step="stepone", index="1")
    DupInputTask.find_task(basic_project_no_flow).add_input_file(
        "test.v", step="steptwo", index="0")

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


@pytest.mark.timeout(120)
def test_rerun_from_after_fork_to_join(forkjoin_project):
    """Re-running with option.from after a fork and option.to at the join
    must forward the bypassed leg's prior SUCCESS so the join can launch.

    Regression for a bug where __configure_collect_previous_information
    only loaded prior manifests for nodes upstream of option.from,
    silently dropping fork-sibling legs that re-converge downstream.
    """
    assert forkjoin_project.run()
    for step in ("entry", "A1", "A2", "B1", "B2", "joinstep"):
        assert forkjoin_project.history("job0").get(
            "record", "status", step=step, index="0"
        ) == NodeStatus.SUCCESS

    forkjoin_project.set("option", "from", ["A1"])
    forkjoin_project.set("option", "to", ["joinstep"])
    assert forkjoin_project.run()

    rec = forkjoin_project.history("job0")
    # Bypassed leg keeps its prior SUCCESS so joinstep sees a satisfied dep.
    assert rec.get("record", "status", step="B1", index="0") == NodeStatus.SUCCESS
    assert rec.get("record", "status", step="B2", index="0") == NodeStatus.SUCCESS
    # Active leg and join re-ran successfully.
    assert rec.get("record", "status", step="A1", index="0") == NodeStatus.SUCCESS
    assert rec.get("record", "status", step="A2", index="0") == NodeStatus.SUCCESS
    assert rec.get("record", "status", step="joinstep", index="0") == NodeStatus.SUCCESS


@pytest.mark.timeout(120)
def test_rerun_from_after_fork_to_join_with_clean(forkjoin_project):
    """Same scenario as test_rerun_from_after_fork_to_join but with
    option.clean=True, which takes the other branch in
    __configure_collect_previous_information."""
    assert forkjoin_project.run()

    forkjoin_project.set("option", "from", ["A1"])
    forkjoin_project.set("option", "to", ["joinstep"])
    forkjoin_project.set("option", "clean", True)
    assert forkjoin_project.run()

    rec = forkjoin_project.history("job0")
    assert rec.get("record", "status", step="B2", index="0") == NodeStatus.SUCCESS
    assert rec.get("record", "status", step="joinstep", index="0") == NodeStatus.SUCCESS


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


@pytest.mark.timeout(60)
def test_resume_value_changed_not_before_from(gcd_nop_project):
    EditableSchema(gcd_nop_project).insert("option", "testing", Parameter("str"))

    assert gcd_nop_project.run()
    run_copy = gcd_nop_project.copy()
    time.sleep(1)  # delay to ensure timestamps differ

    # Change require list
    assert gcd_nop_project.set("tool", "builtin", "task", "nop", "require", "option,testing",
                               step="steptwo", index="0")
    assert gcd_nop_project.set("option", "testing", "thistest")
    gcd_nop_project.logger.setLevel(logging.DEBUG)
    gcd_nop_project.option.add_from("stepthree")
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

    with open("build/gcd/job0/job.log", "r") as f:
        log_text = f.read()
        assert "steptwo/0 requires a rerun but is not in the current execution flow, skipping" \
            in log_text


def test_check_tool_requirements_local(project_logger, gcd_nop_project, caplog):
    project_logger(gcd_nop_project)
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


def test_check_tool_requirements_remote(project_logger, gcd_nop_project, caplog):
    project_logger(gcd_nop_project)
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
def test_check_tool_requirements_non_local(project_logger, gcd_nop_project, caplog, scheduler):
    project_logger(gcd_nop_project)
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


def test_check_tool_requirements_pass(project_logger, gcd_nop_project, caplog):
    project_logger(gcd_nop_project)
    gcd_nop_project.logger.setLevel(logging.INFO)

    EditableSchema(gcd_nop_project).insert("option", "testing", Parameter("str"))
    assert gcd_nop_project.set("option", "testing", "thistest")

    # Change set requirement
    assert gcd_nop_project.set("tool", "builtin", "task", "nop", "require", "option,testing",
                               step="stepthree", index="0")
    assert Scheduler(gcd_nop_project)._Scheduler__check_tool_requirements() is True

    assert caplog.text == ""


def test_install_file_logger(basic_project):
    """Test that __install_file_logger creates job.log and handles backup files with timestamps."""
    import glob as glob_module
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

    # Check that a timestamped backup was created (job.{timestamp}.log)
    backup_files = glob_module.glob(os.path.join(jobdir(basic_project), "job.*.log"))
    backup_files = [f for f in backup_files if os.path.basename(f) != "job.log"]
    assert len(backup_files) == 1

    # Check backup content
    with open(backup_files[0], "r") as f:
        assert f.read() == "existing log content"


@pytest.mark.timeout(90)
def test_install_file_logger_multiple_backups(basic_project):
    """Test that __install_file_logger handles multiple timestamped backup files."""
    import glob as glob_module
    scheduler = Scheduler(basic_project)

    # Create job directory
    os.makedirs(jobdir(basic_project), exist_ok=True)

    # Create existing job.log and some timestamped backups
    existing_log = os.path.join(jobdir(basic_project), "job.log")
    with open(existing_log, "w") as f:
        f.write("log 1")

    backup1 = os.path.join(jobdir(basic_project), "job.20260101-100000.log")
    with open(backup1, "w") as f:
        f.write("backup 1")

    backup2 = os.path.join(jobdir(basic_project), "job.20260101-100001.log")
    with open(backup2, "w") as f:
        f.write("backup 2")

    # Call __install_file_logger
    scheduler._Scheduler__install_file_logger()

    # Check that new timestamped backup was created
    backup_files = glob_module.glob(os.path.join(jobdir(basic_project), "job.*.log"))
    backup_files = [f for f in backup_files if os.path.basename(f) != "job.log"]
    assert len(backup_files) == 3

    # Verify the most recent backup has the current log content
    newest_backup = sorted(backup_files)[-1]
    with open(newest_backup, "r") as f:
        assert f.read() == "log 1"


@pytest.mark.timeout(90)
def test_install_file_logger_no_existing_log(basic_project):
    """Test that __install_file_logger works when no existing log file."""
    import glob as glob_module
    scheduler = Scheduler(basic_project)

    # Create job directory
    os.makedirs(jobdir(basic_project), exist_ok=True)

    # Call __install_file_logger
    scheduler._Scheduler__install_file_logger()

    # Check that new log exists
    existing_log = os.path.join(jobdir(basic_project), "job.log")
    assert os.path.exists(existing_log)

    # Check that no backup was created
    backup_files = glob_module.glob(os.path.join(jobdir(basic_project), "job.*.log"))
    backup_files = [f for f in backup_files if os.path.basename(f) != "job.log"]
    assert len(backup_files) == 0


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


@pytest.mark.timeout(90)
def test_install_file_logger_max_backups(basic_project):
    """Test that __install_file_logger enforces maximum backup limit."""
    import glob as glob_module
    scheduler = Scheduler(basic_project)

    # Create job directory
    os.makedirs(jobdir(basic_project), exist_ok=True)

    # Create more than max_log_backups (5) timestamped backup files
    # Using timestamps that will sort correctly
    for i in range(8):
        timestamp = f"20260101-{100000 + i:06d}"
        backup_file = os.path.join(jobdir(basic_project), f"job.{timestamp}.log")
        with open(backup_file, "w") as f:
            f.write(f"backup {i}")

    initial_backups = glob_module.glob(os.path.join(jobdir(basic_project), "job.*.log"))
    initial_backups = [f for f in initial_backups if os.path.basename(f) != "job.log"]
    assert len(initial_backups) == 8

    # Create current job.log
    existing_log = os.path.join(jobdir(basic_project), "job.log")
    with open(existing_log, "w") as f:
        f.write("current log")

    # Call __install_file_logger
    scheduler._Scheduler__install_file_logger()

    # Check that backups are limited to max_log_backups (5)
    backup_files = glob_module.glob(os.path.join(jobdir(basic_project), "job.*.log"))
    backup_files = [f for f in backup_files if os.path.basename(f) != "job.log"]
    assert len(backup_files) <= 5, f"Expected <= 5 backups, got {len(backup_files)}"

    # Verify the newest backup contains the current log content
    if backup_files:
        newest_backup = sorted(backup_files)[-1]
        with open(newest_backup, "r") as f:
            content = f.read()
            assert "current log" in content or content == "current log"
        with open(newest_backup, "r") as f:
            content = f.read()
            assert "current log" in content or content == "current log"


def test_check_tool_versions_local_pass(project_logger, gcd_nop_project, caplog):
    project_logger(gcd_nop_project)
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


def test_check_tool_versions_local_pass_not_received(project_logger, gcd_nop_project, caplog):
    project_logger(gcd_nop_project)
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


def test_check_tool_versions_remote(project_logger, gcd_nop_project, caplog):
    project_logger(gcd_nop_project)
    gcd_nop_project.logger.setLevel(logging.INFO)

    gcd_nop_project.option.set_remote(True)

    assert gcd_nop_project.set("tool", "builtin", "task", "nop", "exe", "this.exe")

    with patch("siliconcompiler.scheduler.SchedulerNode.get_exe_path") as get_exe_path, \
            patch("siliconcompiler.scheduler.SchedulerNode.check_version") as check_version:
        assert Scheduler(gcd_nop_project)._Scheduler__check_tool_versions() is True
        get_exe_path.assert_not_called()
        check_version.assert_not_called()

    assert caplog.text == ""


def test_check_tool_versions_local_fail(project_logger, gcd_nop_project, caplog):
    project_logger(gcd_nop_project)
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
def test_check_tool_versions_non_local_fail(project_logger, gcd_nop_project, caplog, scheduler):
    project_logger(gcd_nop_project)
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
def test_check_tool_versions_non_local_pass(project_logger, gcd_nop_project, caplog, scheduler):
    project_logger(gcd_nop_project)
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


def test_collect_additional_files_slurm(gcd_additional_files_project, monkeypatch):
    """This test ensures that when collecting files and directories in a
    Slurm scheduled job, the files and directories are correctly copied to
    the sc_collected_files directory within the job directory.
    """
    def mock_slurm_assert():
        return True

    def mock_run(self, project):
        pass

    monkeypatch.setattr(SlurmSchedulerNode, 'run', mock_run)
    monkeypatch.setattr(SlurmSchedulerNode, 'assert_slurm', mock_slurm_assert)

    gcd_additional_files_project.option.scheduler.set_name("slurm")
    gcd_additional_files_project.option.scheduler.set_queue("dummyqueue")

    # Expect this to fail because Slurm execution is mocked
    try:
        gcd_additional_files_project.run()
    except Exception as e:
        assert "Could not run final steps (node2)" in str(e)

    rundir = Path(jobdir(gcd_additional_files_project))

    assert (rundir / "sc_collected_files").exists()
    assert any(f.name.startswith("node1_file_") for f in (rundir / "sc_collected_files").iterdir())
    assert any(d.name.startswith("node1_dir_") for d in (rundir / "sc_collected_files").iterdir())
    assert any(f.name.startswith("node2_file_") for f in (rundir / "sc_collected_files").iterdir())
    assert any(d.name.startswith("node2_dir_") for d in (rundir / "sc_collected_files").iterdir())


def test_skip_collect_additional_files_slurm(gcd_additional_files_project):
    """This test makes sure that running tasks with additional files, on a local scheduler,
    does not collect additional files into the sc_collected_files directory.
    """

    gcd_additional_files_project.run()

    rundir = Path(jobdir(gcd_additional_files_project))

    assert not (rundir / "sc_collected_files").exists()


def test_scruntime_error_init_no_flow():
    """Verify SCRuntimeError is raised during init when flow is not specified"""
    proj = Project(Design("testdesign"))

    with pytest.raises(SCRuntimeError, match="flow must be specified"):
        Scheduler(proj)


def test_scruntime_error_init_invalid_flow(basic_project):
    """Verify SCRuntimeError is raised when flow doesn't exist"""
    basic_project.set("option", "flow", "nonexistent")

    with pytest.raises(SCRuntimeError, match="flow is not defined"):
        Scheduler(basic_project)


def test_run_sweeps_data_source_cache(basic_project):
    """The run collects stale cache entries before resolving anything itself."""
    scheduler = Scheduler(basic_project)

    with patch("siliconcompiler.scheduler.scheduler.auto_cleanup") as sweep, \
            patch.object(scheduler, "check_manifest", return_value=False):
        with pytest.raises(SCRuntimeError, match="check_manifest"):
            scheduler.run()

    sweep.assert_called_once_with(basic_project)


def test_scruntime_error_run_manifest_check(basic_project):
    """Verify check_manifest failure raises SCRuntimeError during run"""
    scheduler = Scheduler(basic_project)

    with patch.object(scheduler, "check_manifest", return_value=False):
        with pytest.raises(SCRuntimeError, match="check_manifest"):
            try:
                scheduler.run()
            finally:
                pass


def test_scruntime_error_run_task_classes(basic_project):
    """Verify task class validation failure raises SCRuntimeError"""
    scheduler = Scheduler(basic_project)

    with patch.object(scheduler, "check_manifest", return_value=True), \
            patch.object(scheduler, "_Scheduler__init_schedulers"), \
            patch.object(scheduler, "_Scheduler__run_setup"), \
            patch.object(scheduler, "configure_nodes"), \
            patch.object(scheduler, "_Scheduler__check_task_classes", return_value=False):
        with pytest.raises(SCRuntimeError, match="Task classes are missing"):
            scheduler.run()


def test_scruntime_error_dashboard_stopped(basic_project):
    """Verify dashboard.stop() is called when unexpected exceptions occur during run"""
    scheduler = Scheduler(basic_project)
    mock_dashboard = MagicMock()
    basic_project._Project__dashboard = mock_dashboard

    # Dashboard is stopped when an unexpected exception (ValueError) is converted to SCRuntimeError
    with patch.object(scheduler, "check_manifest", return_value=True), \
            patch.object(scheduler, "_Scheduler__init_schedulers"), \
            patch.object(scheduler, "_Scheduler__run_setup"), \
            patch.object(scheduler, "configure_nodes"), \
            patch.object(scheduler, "_Scheduler__check_task_classes", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_versions", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_requirements", return_value=True), \
            patch.object(scheduler, "_Scheduler__clean_build_dir_incr"), \
            patch.object(scheduler, "_Scheduler__check_flowgraph_io", return_value=True), \
            patch.object(scheduler, "run_core", side_effect=ValueError("Unexpected")):
        with pytest.raises(SCRuntimeError):
            scheduler.run()

    # Dashboard should be stopped when exception occurs
    mock_dashboard.stop.assert_called()


def test_scruntime_error_mpmanager_notified(basic_project):
    """Verify MPManager.error() is called on unexpected exceptions during run"""
    scheduler = Scheduler(basic_project)

    # MPManager is notified when an unexpected exception occurs
    with patch.object(scheduler, "check_manifest", return_value=True), \
            patch.object(scheduler, "_Scheduler__init_schedulers"), \
            patch.object(scheduler, "_Scheduler__run_setup"), \
            patch.object(scheduler, "configure_nodes"), \
            patch.object(scheduler, "_Scheduler__check_task_classes", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_versions", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_requirements", return_value=True), \
            patch.object(scheduler, "_Scheduler__clean_build_dir_incr"), \
            patch.object(scheduler, "_Scheduler__check_flowgraph_io", return_value=True), \
            patch.object(scheduler, "run_core", side_effect=RuntimeError("Test error")), \
            patch.object(MPManager, "error") as mock_error:
        with pytest.raises(SCRuntimeError):
            scheduler.run()

    # MPManager should be notified of error
    mock_error.assert_called()


def test_unexpected_exception_converted_to_scruntime_error(basic_project):
    """Verify unexpected exceptions are converted to SCRuntimeError"""
    scheduler = Scheduler(basic_project)
    unexpected_error = ValueError("Something unexpected")

    with patch.object(scheduler, "check_manifest", return_value=True), \
            patch.object(scheduler, "_Scheduler__init_schedulers"), \
            patch.object(scheduler, "_Scheduler__run_setup"), \
            patch.object(scheduler, "configure_nodes"), \
            patch.object(scheduler, "_Scheduler__check_task_classes", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_versions", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_requirements", return_value=True), \
            patch.object(scheduler, "_Scheduler__clean_build_dir_incr"), \
            patch.object(scheduler, "_Scheduler__check_flowgraph_io", return_value=True), \
            patch.object(scheduler, "run_core", side_effect=unexpected_error):

        with pytest.raises(SCRuntimeError):
            scheduler.run()


def test_unexpected_exception_logged(basic_project):
    """Verify unexpected exceptions are logged with traceback"""
    scheduler = Scheduler(basic_project)
    unexpected_error = ValueError("Something unexpected")

    with patch.object(scheduler, "check_manifest", return_value=True), \
            patch.object(scheduler, "_Scheduler__init_schedulers"), \
            patch.object(scheduler, "_Scheduler__run_setup"), \
            patch.object(scheduler, "configure_nodes"), \
            patch.object(scheduler, "_Scheduler__check_task_classes", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_versions", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_requirements", return_value=True), \
            patch.object(scheduler, "_Scheduler__clean_build_dir_incr"), \
            patch.object(scheduler, "_Scheduler__check_flowgraph_io", return_value=True), \
            patch.object(scheduler, "run_core", side_effect=unexpected_error):

        # Exception should be logged and converted to SCRuntimeError
        with pytest.raises(SCRuntimeError, match="Something unexpected"):
            scheduler.run()


def test_unexpected_exception_dashboard_stopped(basic_project):
    """Verify dashboard.stop() is called on unexpected exceptions"""
    scheduler = Scheduler(basic_project)
    mock_dashboard = MagicMock()
    basic_project._Project__dashboard = mock_dashboard
    unexpected_error = ValueError("Something unexpected")

    with patch.object(scheduler, "check_manifest", return_value=True), \
            patch.object(scheduler, "_Scheduler__init_schedulers"), \
            patch.object(scheduler, "_Scheduler__run_setup"), \
            patch.object(scheduler, "configure_nodes"), \
            patch.object(scheduler, "_Scheduler__check_task_classes", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_versions", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_requirements", return_value=True), \
            patch.object(scheduler, "_Scheduler__clean_build_dir_incr"), \
            patch.object(scheduler, "_Scheduler__check_flowgraph_io", return_value=True), \
            patch.object(scheduler, "run_core", side_effect=unexpected_error):

        with pytest.raises(SCRuntimeError):
            scheduler.run()

    mock_dashboard.stop.assert_called()


def test_keyboard_interrupt_handled(basic_project):
    """Verify KeyboardInterrupt is handled gracefully"""
    scheduler = Scheduler(basic_project)

    with patch.object(scheduler, "check_manifest", return_value=True), \
            patch.object(scheduler, "_Scheduler__init_schedulers"), \
            patch.object(scheduler, "_Scheduler__run_setup"), \
            patch.object(scheduler, "configure_nodes"), \
            patch.object(scheduler, "_Scheduler__check_task_classes", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_versions", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_requirements", return_value=True), \
            patch.object(scheduler, "_Scheduler__clean_build_dir_incr"), \
            patch.object(scheduler, "_Scheduler__check_flowgraph_io", return_value=True), \
            patch.object(scheduler, "run_core", side_effect=KeyboardInterrupt()):

        # KeyboardInterrupt should be caught and handled without re-raising
        scheduler.run()


def test_keyboard_interrupt_logger_cleanup(basic_project):
    """Verify logger is cleaned up even on KeyboardInterrupt"""
    scheduler = Scheduler(basic_project)

    with patch.object(scheduler, "check_manifest", return_value=True), \
            patch.object(scheduler, "_Scheduler__init_schedulers"), \
            patch.object(scheduler, "_Scheduler__run_setup"), \
            patch.object(scheduler, "configure_nodes"), \
            patch.object(scheduler, "_Scheduler__check_task_classes", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_versions", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_requirements", return_value=True), \
            patch.object(scheduler, "_Scheduler__clean_build_dir_incr"), \
            patch.object(scheduler, "_Scheduler__check_flowgraph_io", return_value=True), \
            patch.object(scheduler, "run_core", side_effect=KeyboardInterrupt()):

        scheduler.run()

    # Handler should be cleaned up
    assert isinstance(scheduler._Scheduler__joblog_handler, logging.NullHandler)


def test_logger_cleanup_on_manifest_error(basic_project):
    """Verify logger handler is cleaned up after manifest check error"""
    scheduler = Scheduler(basic_project)

    with patch.object(scheduler, "check_manifest", return_value=False):
        try:
            scheduler.run()
        except SCRuntimeError:
            pass

    # Handler should be reset to NullHandler
    assert isinstance(scheduler._Scheduler__joblog_handler, logging.NullHandler)


def test_logger_cleanup_on_unexpected_exception(basic_project):
    """Verify logger handler is cleaned up even on unexpected exceptions"""
    scheduler = Scheduler(basic_project)

    with patch.object(scheduler, "check_manifest", return_value=True), \
            patch.object(scheduler, "_Scheduler__init_schedulers"), \
            patch.object(scheduler, "_Scheduler__run_setup"), \
            patch.object(scheduler, "configure_nodes"), \
            patch.object(scheduler, "_Scheduler__check_task_classes", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_versions", return_value=True), \
            patch.object(scheduler, "_Scheduler__check_tool_requirements", return_value=True), \
            patch.object(scheduler, "_Scheduler__clean_build_dir_incr"), \
            patch.object(scheduler, "_Scheduler__check_flowgraph_io", return_value=True), \
            patch.object(scheduler, "run_core", side_effect=RuntimeError("Test")):
        try:
            scheduler.run()
        except (SCRuntimeError, RuntimeError):
            pass

    # Handler should be reset to NullHandler even after exception
    assert isinstance(scheduler._Scheduler__joblog_handler, logging.NullHandler)


def test_logger_cleanup_on_manifest_exception(basic_project):
    """Verify logger is cleaned up even when manifest check raises exception"""
    scheduler = Scheduler(basic_project)

    with patch.object(scheduler, "check_manifest", side_effect=RuntimeError("Manifest error")):
        try:
            scheduler.run()
        except (SCRuntimeError, RuntimeError):
            pass

    # Handler should be cleaned up
    assert isinstance(scheduler._Scheduler__joblog_handler, logging.NullHandler)


@pytest.mark.skipif(not sys.platform.startswith("linux"),
                    reason="unguarded module-level run() is only supported on linux, "
                           "where the fork start method is pinned")
def test_unguarded_run_with_non_fork_default():
    '''Regression: an unguarded module-level ``proj.run()`` script must succeed
    even when the interpreter's default start method is not fork.

    Python 3.14 changed the POSIX default to ``forkserver``; both it and
    ``spawn`` re-import ``__main__`` and would recurse into the multiprocessing
    "bootstrapping phase" RuntimeError for a script without an
    ``if __name__ == "__main__"`` guard. SiliconCompiler pins fork on Linux for
    every process it launches (node workers, the run-check pool and the
    SyncManager), so this must work regardless of the default. This runs twice:
    a clean run and a re-run (the re-run exercises the check pool, which is
    skipped on a clean run).'''
    # The test already runs in its own isolated cwd (autouse test_wrapper
    # fixture), so write the script and let its build dir land there.
    script = Path("unguarded_flow.py")
    # NOTE: deliberately NO ``if __name__ == "__main__"`` guard, and the default
    # start method is forced to spawn to emulate a hostile (non-fork) default.
    script.write_text(textwrap.dedent(
        """
        import multiprocessing
        multiprocessing.set_start_method("spawn", force=True)

        from siliconcompiler import Design, Project, Flowgraph
        from siliconcompiler.tools.builtin.nop import NOPTask

        design = Design("testdesign")
        with design.active_fileset("rtl"):
            design.set_topmodule("designtop")

        proj = Project(design)
        proj.add_fileset("rtl")

        flow = Flowgraph("testflow")
        flow.node("stepone", NOPTask())
        flow.node("steptwo", NOPTask())
        flow.edge("stepone", "steptwo")
        proj.set_flow(flow)

        proj.run()
        print("SC_RUN_OK")
        """))

    for run in ("clean", "rerun"):
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=120)
        combined = proc.stdout + proc.stderr
        assert proc.returncode == 0, f"[{run}] failed:\n{combined}"
        assert "SC_RUN_OK" in proc.stdout, f"[{run}] missing success marker:\n{combined}"
        assert "bootstrapping phase" not in combined, \
            f"[{run}] hit the multiprocessing guard error:\n{combined}"


###########################
# cancel
###########################

def test_cancel_reaches_the_task_scheduler(gcd_nop_project):
    '''A cancel arriving mid-run is handed straight down'''
    scheduler = Scheduler(gcd_nop_project)

    task_scheduler = MagicMock()
    scheduler._Scheduler__task_scheduler = task_scheduler

    scheduler.cancel()

    task_scheduler.cancel.assert_called_once_with()


def test_cancel_during_setup_is_held_for_the_task_scheduler(gcd_nop_project):
    '''Setup is the long part of a run, and the scheduler that executes nodes
       does not exist until the end of it.

    A cancel landing in that window has nothing to hand the request to, so this
    scheduler keeps it and applies it the moment there is one -- before any node
    is launched.
    '''
    scheduler = Scheduler(gcd_nop_project)
    scheduler.cancel()

    canceled = []
    with patch("siliconcompiler.scheduler.scheduler.TaskScheduler") as task_scheduler_cls:
        task_scheduler_cls.return_value.cancel.side_effect = \
            lambda: canceled.append("cancel")
        task_scheduler_cls.return_value.run.side_effect = \
            lambda *_: canceled.append("run")
        scheduler.run_core()

    # Canceled before it was ever asked to run, so the run loop starts on a
    # scheduler that already knows the run is over.
    assert canceled == ["cancel", "run"]


def test_cancel_with_no_task_scheduler(gcd_nop_project):
    '''A cancel before run_core() has nothing to forward to, and says so by
       doing nothing rather than failing'''
    Scheduler(gcd_nop_project).cancel()


def test_project_publishes_its_scheduler(gcd_nop_project):
    '''What a caller holding the project has to work with, since the run it
       started keeps its scheduler on the stack'''
    scheduler = MagicMock()
    gcd_nop_project._Project__scheduler = scheduler

    assert gcd_nop_project._scheduler is scheduler


def test_project_scheduler_without_a_run():
    '''No run in progress is not an error, it is None'''
    design = Design("designtop")
    with design.active_fileset("rtl"):
        design.set_topmodule("designtop")

    assert Project(design)._scheduler is None


def test_project_drops_its_scheduler_when_the_run_ends(gcd_nop_project):
    '''The handle lives exactly as long as there is a run to stop'''
    # history() is stubbed as well: run() returns the completed job's record,
    # and a stubbed run never produced one.
    with patch.object(Scheduler, "run"), patch.object(Project, "history"):
        gcd_nop_project.run()

    assert gcd_nop_project._scheduler is None


def test_project_scheduler_is_not_serialized(gcd_nop_project):
    '''A live scheduler holds locks and log handlers that do not pickle, and
       means nothing to the node process or history copy being made'''
    gcd_nop_project._Project__scheduler = Scheduler(gcd_nop_project)

    assert "_Project__scheduler" not in gcd_nop_project.__getstate__()
    assert gcd_nop_project.copy()._scheduler is None


# ---------------------------------------------------------------------------
# [option,continue] across a whole run
#
# The option excuses a node's failure for the benefit of everything downstream:
# an excused branch supplies nothing, so a fan-in assembles the branches that
# survived. It is read from the node that failed, never from the node that
# consumes it, and it is inert on any flow that does not set it.
#
# The gates themselves are unit-tested next to their own code -- the launch
# decision in test_taskscheduler.py, input forwarding and validation in
# test_schedulernode.py, the Task-level rules in test_tool.py. These are the
# real runs that prove the pieces are wired together.
# ---------------------------------------------------------------------------


class ContinueTask(Task):
    """A task with no file I/O, so only the node-status gates are in play."""

    def __init__(self):
        super().__init__()
        self.add_parameter("fail", "bool", "return a nonzero exit code")

    def tool(self):
        return "continuetool"

    def task(self):
        return "noio"

    def setup(self):
        # 'require' is what drives change detection, so flipping the flag on a
        # re-run re-runs the node instead of reusing its previous result.
        self.add_required_key("var", "fail")

    def run(self):
        return 1 if self.get("var", "fail") else 0


class ContinueDataTask(ContinueTask):
    """Declares its inputs from whatever its upstreams offer, and records what
    actually arrived so a test can assert on the fan-in."""

    def __init__(self):
        super().__init__()
        self.add_parameter("skip", "bool", "skip this node instead of running it")

    def task(self):
        return "data"

    def outfile(self):
        return f"output.{self.step}.{self.index}.txt"

    def setup(self):
        # Skipped before anything is declared: a node that never runs must not
        # be held to outputs it never promised.
        if self.get("var", "skip"):
            raise TaskSkip("skipped")

        super().setup()
        self.add_input_file(sorted(self.get_files_from_input_nodes().keys()))
        self.add_output_file(self.outfile())

    def run(self):
        if self.get("var", "fail"):
            # Fails before writing anything, so a consumer that sees this
            # node's output saw a stale one.
            return 1

        Path("outputs").mkdir(exist_ok=True)
        received = sorted(f.name for f in os.scandir("inputs") if f.name.endswith(".txt"))
        Path("outputs", self.outfile()).write_text("\n".join(received))
        return 0


class ContinueNoisyTask(ContinueTask):
    """Exits cleanly but reports errors in its metrics."""

    def task(self):
        return "noisy"

    def post_process(self):
        self.record_metric("errors", 3)


class ContinueBinTask(ContinueTask):
    """Builds the binary for one shard of a constrained-random sweep."""

    def task(self):
        return "bin"

    def setup(self):
        super().setup()
        self.add_output_file(f"shard.{self.index}.elf")

    def run(self):
        if self.get("var", "fail"):
            return 1

        Path("outputs").mkdir(exist_ok=True)
        Path("outputs", f"shard.{self.index}.elf").write_text("elf")
        return 0


class ContinueSimTask(Task):
    """Runs one shard. A simulator handed no binary has nothing to run."""

    def tool(self):
        return "continuetool"

    def task(self):
        return "sim"

    def setup(self):
        self.add_input_file(sorted(self.get_files_from_input_nodes().keys()))
        self.add_output_file(f"coverage.{self.index}.db")

    def run(self):
        if not any(f.name.endswith(".elf") for f in os.scandir("inputs")):
            self.logger.error("no binary to simulate")
            return 1

        Path("outputs").mkdir(exist_ok=True)
        Path("outputs", f"coverage.{self.index}.db").write_text(f"shard {self.index}")
        return 0


class ContinueMergeTask(Task):
    """Merges the coverage databases that arrived."""

    def tool(self):
        return "continuetool"

    def task(self):
        return "merge"

    def setup(self):
        self.add_input_file(sorted(self.get_files_from_input_nodes().keys()))
        self.add_output_file("coverage.total.db")

    def run(self):
        merged = sorted(f.name for f in os.scandir("inputs") if f.name.endswith(".db"))
        Path("outputs").mkdir(exist_ok=True)
        Path("outputs", "coverage.total.db").write_text("\n".join(merged))
        return 0


@pytest.fixture
def continue_project():
    """Bare project for the flows below, which each build their own flowgraph."""
    def make():
        design = Design("continuetest")
        with design.active_fileset("rtl"):
            design.set_topmodule("top")
        project = Project(design)
        project.add_fileset("rtl")
        return project
    return make


@pytest.fixture
def continue_diamond(continue_project):
    """A -> {B, C} -> D, with one branch set to fail."""
    def make(task_cls, fail_step="B"):
        flow = Flowgraph("diamond")
        for step in ("A", "B", "C", "D"):
            flow.node(step, task_cls())
        flow.edge("A", "B")
        flow.edge("A", "C")
        flow.edge("B", "D")
        flow.edge("C", "D")

        project = continue_project()
        project.set_flow(flow)

        # Every node needs the flag set, both so 'require' is satisfied and so
        # flipping one later reads as a change rather than as a first assignment.
        task = task_cls.find_task(project)
        for step in ("A", "B", "C", "D"):
            task.set("var", "fail", step == fail_step, step=step)
        return project
    return make


@pytest.fixture
def continue_fanout(continue_project):
    """compile -> bin0..binN -> sim0..simN -> merge, the shape of issue #5368."""
    def make(width=3, fail_indexes=(0,)):
        flow = Flowgraph("fanout")
        flow.node("compile", ContinueTask())
        flow.node("merge", ContinueMergeTask())
        for index in range(width):
            flow.node("bin", ContinueBinTask(), index=index)
            flow.node("sim", ContinueSimTask(), index=index)
            flow.edge("compile", "bin", head_index=index)
            flow.edge("bin", "sim", tail_index=index, head_index=index)
            flow.edge("sim", "merge", tail_index=index)

        project = continue_project()
        project.set_flow(flow)

        ContinueTask.find_task(project).set("var", "fail", False, step="compile")
        bin_task = ContinueBinTask.find_task(project)
        for index in range(width):
            bin_task.set("var", "fail", index in fail_indexes, step="bin", index=index)
        return project
    return make


@pytest.fixture
def continue_chain(continue_project):
    """A -> B, A reporting errors in its metrics rather than exiting nonzero."""
    def make():
        flow = Flowgraph("metricflow")
        flow.node("A", ContinueNoisyTask())
        flow.node("B", ContinueTask())
        flow.edge("A", "B")

        project = continue_project()
        project.set_flow(flow)
        ContinueNoisyTask.find_task(project).set("var", "fail", False, step="A")
        ContinueTask.find_task(project).set("var", "fail", False, step="B")
        return project
    return make


@pytest.fixture
def continue_join(continue_project):
    """A and B both feed a builtin join, with A set to fail."""
    def make():
        flow = Flowgraph("joinflow")
        flow.node("A", ContinueDataTask())
        flow.node("B", ContinueDataTask())
        flow.node("join", JoinTask())
        flow.edge("A", "join")
        flow.edge("B", "join")

        project = continue_project()
        project.set_flow(flow)

        task = ContinueDataTask.find_task(project)
        task.set("var", "fail", True, step="A")
        task.set("var", "fail", False, step="B")
        return project
    return make


def _joblog(project, job="job0"):
    """The run's own log. Records emitted inside a node reach the parent through
    the log queue, which dispatches to handlers directly, so they never appear
    in caplog -- but they do land here."""
    return Path("build", project.name, job, "job.log").read_text()


def _status(project, step, index="0", job="job0"):
    return project.history(job).get("record", "status", step=step, index=index)


def _node_dir(project, step, index="0", job="job0"):
    return os.path.join("build", project.name, job, step, index)


#
# The reporter's two cases from issue #5368.
#

@pytest.mark.timeout(60)
def test_continue_diamond_no_files(continue_diamond):
    """A failed branch must not abort a sibling branch when continue is enabled."""
    project = continue_diamond(ContinueTask)
    project.option.set_continue(True, step="B")

    assert project.run()

    assert _status(project, "A") == NodeStatus.SUCCESS
    assert _status(project, "B") == NodeStatus.ERROR
    assert _status(project, "C") == NodeStatus.SUCCESS
    assert _status(project, "D") == NodeStatus.SUCCESS


@pytest.mark.timeout(60)
def test_continue_diamond_with_files(continue_diamond):
    """The same, with files passed between nodes: the requirement set shrinks."""
    project = continue_diamond(ContinueDataTask)
    project.option.set_continue(True, step="B")

    assert project.run()

    assert _status(project, "A") == NodeStatus.SUCCESS
    assert _status(project, "B") == NodeStatus.ERROR
    assert _status(project, "C") == NodeStatus.SUCCESS
    assert _status(project, "D") == NodeStatus.SUCCESS

    # D ran on C's output alone -- B's branch was dropped, not substituted, so
    # A's output did not take its place either.
    received = Path(_node_dir(project, "D"), "outputs", "output.D.0.txt").read_text()
    assert received.splitlines() == ["output.C.0.txt"]


@pytest.mark.timeout(60)
def test_continue_records_only_the_surviving_input_nodes(continue_diamond):
    """[record,inputnode] must not name a branch nothing was taken from."""
    project = continue_diamond(ContinueDataTask)
    project.option.set_continue(True, step="B")

    assert project.run()

    assert project.history("job0").get(
        "record", "inputnode", step="D", index="0") == [("C", "0")]


@pytest.mark.timeout(120)
def test_continue_does_not_resurrect_a_stale_output(continue_diamond):
    """A failed task must not leave behind outputs that it never produced.

    The diamond on a clean tree cannot catch this: it takes a re-run into a
    build tree where the node that now fails previously succeeded.
    """
    project = continue_diamond(ContinueDataTask, fail_step=None)

    # First run: everything succeeds, so B leaves a real output behind.
    assert project.run()
    stale = Path(_node_dir(project, "B"), "outputs", "output.B.0.txt")
    assert stale.exists()

    # Second run into the same job: B now fails before writing anything.
    ContinueDataTask.find_task(project).set("var", "fail", True, step="B")
    project.option.set_continue(True, step="B")
    assert project.run()

    assert _status(project, "B") == NodeStatus.ERROR
    assert _status(project, "D") == NodeStatus.SUCCESS

    assert not stale.exists(), "the failed node's previous output survived its re-run"
    assert not Path(_node_dir(project, "D"), "inputs", "output.B.0.txt").exists()
    received = Path(_node_dir(project, "D"), "outputs", "output.D.0.txt").read_text()
    assert received.splitlines() == ["output.C.0.txt"]


#
# The shape the issue is actually about: the failure is two levels up from the
# merge, and the node the merge waits on fails as a consequence.
#

@pytest.mark.timeout(120)
def test_continue_fanout_merges_surviving_shards(continue_fanout, caplog):
    """bin0 fails -> sim0 fails as a consequence -> merge runs on the rest."""
    project = continue_fanout(width=3, fail_indexes=(0,))
    # Two calls cover a fan-out of any width: [option,continue] is pernode.
    project.option.set_continue(True, step="bin")
    project.option.set_continue(True, step="sim")

    assert project.run()

    assert _status(project, "bin", "0") == NodeStatus.ERROR
    assert _status(project, "bin", "1") == NodeStatus.SUCCESS
    assert _status(project, "bin", "2") == NodeStatus.SUCCESS

    # sim0 ran and failed -- it was launched on an excused input and had no
    # binary -- rather than being starved before it ever started. The two take
    # different paths through the gates, so name which one it is.
    assert _status(project, "sim", "0") == NodeStatus.ERROR
    assert os.path.isdir(_node_dir(project, "sim", "0"))
    assert _status(project, "sim", "1") == NodeStatus.SUCCESS
    assert _status(project, "sim", "2") == NodeStatus.SUCCESS

    assert _status(project, "merge") == NodeStatus.SUCCESS
    merged = Path(_node_dir(project, "merge"), "outputs", "coverage.total.db").read_text()
    assert merged.splitlines() == ["coverage.1.db", "coverage.2.db"]

    # A green run must not hide the dead branch.
    assert "Run completed with errors in: bin/0, sim/0" in caplog.text


@pytest.mark.timeout(120)
def test_continue_does_not_propagate_down_a_branch(continue_fanout):
    """continue on bin but not sim: sim0's own failure must still halt the flow.

    Marking one node must not quietly excuse everything below it -- which is
    why the answer to the issue is that *both* nodes need marking.
    """
    project = continue_fanout(width=3, fail_indexes=(0,))
    project.option.set_continue(True, step="bin")

    with pytest.raises(RuntimeError,
                       match=r"Could not run final steps \(merge\) due to errors in: "
                             r"bin/0, sim/0"):
        project.run()

    assert _status(project, "bin", "0") == NodeStatus.ERROR
    assert _status(project, "sim", "0") == NodeStatus.ERROR
    assert _status(project, "merge") == NodeStatus.PENDING


@pytest.mark.timeout(120)
def test_continue_on_the_consumer_branch_alone_starves_it(continue_fanout):
    """continue on sim but not bin: sim0 is never launched at all.

    The other of the two failure modes -- the merge's missing input comes from
    a starved predecessor rather than a failed one.
    """
    project = continue_fanout(width=3, fail_indexes=(0,))
    project.option.set_continue(True, step="sim")

    with pytest.raises(RuntimeError,
                       match=r"Could not run final steps \(merge\) due to errors in: bin/0"):
        project.run()

    assert _status(project, "bin", "0") == NodeStatus.ERROR
    assert _status(project, "sim", "0") == NodeStatus.PENDING
    assert not os.path.isdir(_node_dir(project, "sim", "0"))


@pytest.mark.timeout(120)
def test_continue_with_every_input_excused_still_fails(continue_fanout):
    """A merge with nothing to merge is not a success.

    "At least one" behaves differently at k = N, and this is the case where a
    best-effort relaxation would otherwise report a green run over no work.
    """
    project = continue_fanout(width=3, fail_indexes=(0, 1, 2))
    project.option.set_continue(True, step="bin")
    project.option.set_continue(True, step="sim")

    with pytest.raises(RuntimeError,
                       match=r"Could not run final steps \(merge\) due to errors in: "
                             r"bin/0, bin/1, bin/2, merge/0, sim/0, sim/1, sim/2"):
        project.run()

    # Each sim's only input was excused, so each launched, found its fan-in
    # empty and said so, rather than being left pending with no explanation.
    for index in ("0", "1", "2"):
        assert _status(project, "sim", index) == NodeStatus.ERROR
        assert f"No inputs selected for sim/{index}" in _joblog(project)
    assert _status(project, "merge") == NodeStatus.ERROR


#
# Blast radius: the change must be inert unless a node opts in.
#

@pytest.mark.timeout(60)
@pytest.mark.parametrize("task_cls", (ContinueTask, ContinueDataTask))
def test_without_continue_a_failed_branch_still_halts(continue_diamond, task_cls):
    """A task that does not opt in fails exactly as it does today."""
    project = continue_diamond(task_cls)

    with pytest.raises(RuntimeError,
                       match=r"Could not run final steps \(D\) due to errors in: B/0"):
        project.run()

    assert _status(project, "B") == NodeStatus.ERROR
    assert _status(project, "D") == NodeStatus.PENDING


@pytest.mark.timeout(60)
def test_a_global_continue_excuses_every_node(continue_diamond):
    """The CLI switch (-continue) carries no step, and [option,continue] is
    pernode=OPTIONAL, so the global value answers for every node. That is the
    broad form of the option and it has to work -- and be the user's explicit
    choice rather than something a per-node fix leaks into."""
    project = continue_diamond(ContinueDataTask)
    project.option.set_continue(True)

    assert project.run()

    assert _status(project, "B") == NodeStatus.ERROR
    assert _status(project, "D") == NodeStatus.SUCCESS
    received = Path(_node_dir(project, "D"), "outputs", "output.D.0.txt").read_text()
    assert received.splitlines() == ["output.C.0.txt"]


@pytest.mark.timeout(60)
def test_a_skipped_upstream_is_traversed_not_dropped(continue_diamond):
    """The distinction the whole design turns on. A SKIPPED node is
    transparent -- its own inputs stand in for it -- while an excused failure
    supplies nothing at all. Setting continue must not collapse the two: B is
    skipped here, so D still receives A's output through it.
    """
    project = continue_diamond(ContinueDataTask, fail_step=None)
    project.option.set_continue(True)
    # Skip B without failing it.
    ContinueDataTask.find_task(project).set("var", "skip", True, step="B")

    assert project.run()

    assert _status(project, "B") == NodeStatus.SKIPPED
    assert _status(project, "D") == NodeStatus.SUCCESS
    assert project.history("job0").get(
        "record", "inputnode", step="D", index="0") == [("A", "0"), ("C", "0")]

    # A's output arrived through the skipped node, which is exactly what an
    # excused *failure* must not do.
    received = Path(_node_dir(project, "D"), "outputs", "output.D.0.txt").read_text()
    assert received.splitlines() == ["output.A.0.txt", "output.C.0.txt"]


@pytest.mark.timeout(60)
def test_continue_on_an_unrelated_node_does_not_excuse_the_failure(continue_diamond):
    """The excuse is read from the node that failed, not from any other."""
    project = continue_diamond(ContinueTask)
    project.option.set_continue(True, step="C")

    with pytest.raises(RuntimeError,
                       match=r"Could not run final steps \(D\) due to errors in: B/0"):
        project.run()


def test_continue_still_requires_an_input_a_live_node_owes(continue_diamond, caplog):
    """Excusing one branch must not suppress the pre-run validator's finding
    about an input nothing produces. The run refuses to start, as it should."""
    project = continue_diamond(ContinueDataTask)
    project.option.set_continue(True, step="B")
    ContinueDataTask.find_task(project).add_input_file("missing.txt", step="D", index="0")

    with pytest.raises(RuntimeError, match=r"Flowgraph file IO constrains errors"):
        project.run()

    assert "Invalid flow: D/0 will not receive required input missing.txt" in caplog.text


@pytest.mark.timeout(60)
def test_the_metrics_halt_still_halts_without_continue(continue_chain):
    """errors > 0 and no continue is the documented default, and is not in scope."""
    project = continue_chain()

    with pytest.raises(RuntimeError,
                       match=r"Could not run final steps \(B\) due to errors in: A/0"):
        project.run()

    assert "continuetool/noisy reported 3 errors during A/0" in _joblog(project)


@pytest.mark.timeout(60)
def test_the_metrics_halt_is_the_one_place_continue_already_worked(continue_chain):
    """It is also the only gate where continue leaves the node a SUCCESS."""
    project = continue_chain()
    project.option.set_continue(True, step="A")

    assert project.run()

    assert _status(project, "A") == NodeStatus.SUCCESS
    assert _status(project, "B") == NodeStatus.SUCCESS
    assert project.history("job0").get("metric", "errors", step="A", index="0") == 3


@pytest.mark.timeout(60)
def test_a_builtin_join_merges_the_arms_that_survived(continue_join):
    """The builtins were already exempt at the launch gate but died forwarding
    a failed arm's outputs. An excused arm is now dropped instead."""
    project = continue_join()
    project.option.set_continue(True, step="A")

    assert project.run()

    assert _status(project, "A") == NodeStatus.ERROR
    assert _status(project, "join") == NodeStatus.SUCCESS
    assert sorted(f.name for f in os.scandir(os.path.join(_node_dir(project, "join"), "outputs"))
                  if f.name.endswith(".txt")) == ["output.B.0.txt"]


@pytest.mark.timeout(60)
def test_a_builtin_join_with_every_arm_excused_fails_rather_than_stalling(continue_join):
    """Nothing left to join is not a success -- and it must be an ERROR, not a
    node left PENDING. A builtin's own consumers wait on a terminal status just
    like anyone else's, so it launches and says it has nothing to work with."""
    project = continue_join()
    ContinueDataTask.find_task(project).set("var", "fail", True, step="B")
    project.option.set_continue(True, step="A")
    project.option.set_continue(True, step="B")

    with pytest.raises(RuntimeError,
                       match=r"Could not run final steps \(join\) due to errors in: "
                             r"A/0, B/0, join/0"):
        project.run()

    assert _status(project, "join") == NodeStatus.ERROR
    assert "No inputs selected for join/0" in _joblog(project)


@pytest.mark.timeout(60)
def test_a_builtin_join_still_dies_on_an_unexcused_arm(continue_join):
    """Without continue the builtins behave exactly as they do today: the
    launch-gate exemption gets the join started, and forwarding the failed
    arm's outputs then halts it."""
    project = continue_join()

    with pytest.raises(RuntimeError,
                       match=r"Could not run final steps \(join\) due to errors in: A/0"):
        project.run()
