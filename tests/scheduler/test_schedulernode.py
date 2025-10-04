import logging
import os
import pytest
import time

import os.path

from multiprocessing import Queue
from unittest.mock import patch

from siliconcompiler import Project, Flowgraph, Design
from siliconcompiler import NodeStatus
from siliconcompiler import Task
from siliconcompiler import TaskSkip
from siliconcompiler.tools.builtin.nop import NOPTask
from siliconcompiler.tools.builtin.join import JoinTask
from scheduler.tools.echo import EchoTask

from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.utils.paths import jobdir


@pytest.fixture
def project():
    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")

    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    return proj


@pytest.fixture
def echo_project():
    flow = Flowgraph("testflow")
    flow.node("stepone", EchoTask())
    flow.node("steptwo", EchoTask())
    flow.edge("stepone", "steptwo")

    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    return proj


def test_init_invalid_step(project):
    with pytest.raises(TypeError, match="step must be a string with a value"):
        SchedulerNode(project, None, "0")


def test_init_invalid_step_empty(project):
    with pytest.raises(TypeError, match="step must be a string with a value"):
        SchedulerNode(project, "", "0")


def test_init_invalid_index(project):
    with pytest.raises(TypeError, match="index must be a string with a value"):
        SchedulerNode(project, "step", None)


def test_init_invalid_index_int(project):
    with pytest.raises(TypeError, match="index must be a string with a value"):
        SchedulerNode(project, "step", 0)


def test_init_invalid_index_empty(project):
    with pytest.raises(TypeError, match="index must be a string with a value"):
        SchedulerNode(project, "step", "")


def test_init(project):
    node = SchedulerNode(project, "stepone", "0")

    assert node.is_local is True
    assert node.is_builtin is False
    assert node.has_error is False
    assert node.step == "stepone"
    assert node.index == "0"
    assert node.name == "testdesign"
    assert node.topmodule == "top"
    assert node.project is project
    assert node.logger is project.logger
    assert node.jobname == "job0"
    assert node.is_replay is False
    assert isinstance(node.task, Task)
    assert node.jobworkdir == jobdir(project)
    assert node.workdir == os.path.join(node.jobworkdir, "stepone", "0")
    assert node.project_cwd == os.path.abspath(".")
    assert node.collection_dir == os.path.join(node.jobworkdir, "sc_collected_files")

    # Check private fields
    assert node._SchedulerNode__record_user_info is False
    assert node._SchedulerNode__generate_test_case is True
    assert node._SchedulerNode__hash is False
    assert node._SchedulerNode__is_entry_node is True


def test_init_replay(project):
    node = SchedulerNode(project, "stepone", "0", replay=True)

    assert node.is_local is True
    assert node.is_builtin is False
    assert node.has_error is False
    assert node.step == "stepone"
    assert node.index == "0"
    assert node.name == "testdesign"
    assert node.topmodule == "top"
    assert node.project is project
    assert node.logger is project.logger
    assert node.jobname == "job0"
    assert node.is_replay is True
    assert isinstance(node.task, Task)
    assert node.jobworkdir == jobdir(project)
    assert node.workdir == os.path.join(node.jobworkdir, "stepone", "0")
    assert node.project_cwd == os.path.abspath(".")
    assert node.collection_dir == os.path.join(node.jobworkdir, "sc_collected_files")

    # Check private fields
    assert node._SchedulerNode__record_user_info is False
    assert node._SchedulerNode__generate_test_case is False
    assert node._SchedulerNode__hash is False
    assert node._SchedulerNode__is_entry_node is True


def test_init_not_entry(project):
    node = SchedulerNode(project, "steptwo", "0")

    assert node.is_local is True
    assert node.is_builtin is False
    assert node.has_error is False
    assert node.step == "steptwo"
    assert node.index == "0"
    assert node.name == "testdesign"
    assert node.topmodule == "top"
    assert node.project is project
    assert node.logger is project.logger
    assert node.jobname == "job0"
    assert node.is_replay is False
    assert isinstance(node.task, Task)
    assert node.jobworkdir == jobdir(project)
    assert node.workdir == os.path.join(node.jobworkdir, "steptwo", "0")
    assert node.project_cwd == os.path.abspath(".")
    assert node.collection_dir == os.path.join(node.jobworkdir, "sc_collected_files")

    # Check private fields
    assert node._SchedulerNode__record_user_info is False
    assert node._SchedulerNode__generate_test_case is True
    assert node._SchedulerNode__hash is False
    assert node._SchedulerNode__is_entry_node is False


def test_static_init():
    assert SchedulerNode.init(None) is None


def test_set_builtin(project):
    node = SchedulerNode(project, "steptwo", "0")
    assert node.is_builtin is False
    node.set_builtin()
    assert node.is_builtin is True


def test_threads(project):
    node = SchedulerNode(project, "steptwo", "0")
    node.task.set_threads(1)
    with node.runtime():
        assert node.threads == 1
    assert project.set("tool", "builtin", "task", "nop", "threads", 10)
    with node.runtime():
        assert node.threads == 10


def test_get_manifest_output(project):
    node = SchedulerNode(project, "steptwo", "0")
    assert node.get_manifest() == os.path.join(
        node.workdir, "outputs", f"{node.name}.pkg.json")


def test_get_manifest_input(project):
    node = SchedulerNode(project, "steptwo", "0")
    assert node.get_manifest(input=True) == os.path.join(
        node.workdir, "inputs", f"{node.name}.pkg.json")


@pytest.mark.parametrize(
    "type,expect_name", [
        ("exe", "steptwo.log"),
        ("sc", "sc_steptwo_0.log"),
    ])
def test_get_log(project, type, expect_name):
    node = SchedulerNode(project, "steptwo", "0")
    assert node.get_log(type) == os.path.join(
        node.workdir, expect_name)


def test_get_log_invalid(project):
    node = SchedulerNode(project, "steptwo", "0")
    with pytest.raises(ValueError, match="invalid is not a log"):
        node.get_log("invalid")


def test_halt(project):
    node = SchedulerNode(project, "steptwo", "0")
    node.task.setup_work_directory(node.workdir)

    with pytest.raises(SystemExit):
        node.halt()
    assert project.get("record", "status", step="steptwo", index="0") == NodeStatus.ERROR
    assert os.path.exists("build/testdesign/job0/steptwo/0/outputs/testdesign.pkg.json")


def test_halt_with_reason(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    node = SchedulerNode(project, "steptwo", "0")
    node.task.setup_work_directory(node.workdir)

    with pytest.raises(SystemExit):
        node.halt("failed due to error")
    assert project.get("record", "status", step="steptwo", index="0") == NodeStatus.ERROR
    assert os.path.exists("build/testdesign/job0/steptwo/0/outputs/testdesign.pkg.json")
    assert "failed due to error" in caplog.text


def test_setup(project):
    node = SchedulerNode(project, "steptwo", "0")

    with node.runtime():
        assert node.setup() is True


def test_setup_error(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    node = SchedulerNode(project, "steptwo", "0")

    def dummy_setup(*_args, **_kwargs):
        raise ValueError("Find this")  # noqa
    monkeypatch.setattr(node.task, "setup", dummy_setup)

    with node.runtime():
        with pytest.raises(ValueError, match="Find this"):
            node.setup()
    assert "Failed to run setup() for steptwo/0 with builtin/nop" in caplog.text


def test_setup_with_return(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    node = SchedulerNode(project, "steptwo", "0")

    def dummy_setup(*_args, **_kwargs):
        return "This should not be there"
    monkeypatch.setattr(node.task, "setup", dummy_setup)

    with node.runtime():
        with pytest.raises(RuntimeError,
                           match=r"setup\(\) returned a value, but should not have: "
                           "This should not be there"):
            node.setup()
    assert "Failed to run setup() for steptwo/0 with builtin/nop" in caplog.text


def test_setup_skipped(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    node = SchedulerNode(project, "steptwo", "0")

    def dummy_setup(*_args, **_kwargs):
        raise TaskSkip("skip me")  # noqa
    monkeypatch.setattr(node.task, "setup", dummy_setup)

    with node.runtime():
        assert node.setup() is False
    assert project.get("record", "status", step="steptwo", index="0") == NodeStatus.SKIPPED
    assert "Removing steptwo/0 due to skip me" in caplog.text


def test_clean_directory(project):
    node = SchedulerNode(project, "steptwo", "0")
    os.makedirs(node.workdir, exist_ok=True)
    assert os.path.exists(node.workdir)
    node.clean_directory()
    assert not os.path.exists(node.workdir)


def test_clean_directory_no_dir(project):
    node = SchedulerNode(project, "steptwo", "0")
    assert not os.path.exists(node.workdir)
    node.clean_directory()
    assert not os.path.exists(node.workdir)


def test_get_check_changed_keys(project):
    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        values, paths = node.get_check_changed_keys()
    assert values == {
        ('tool', 'builtin', 'task', 'nop', 'threads'),
        ('tool', 'builtin', 'task', 'nop', 'option')
    }
    assert paths == {
        ('tool', 'builtin', 'task', 'nop', 'refdir'),
        ('tool', 'builtin', 'task', 'nop', 'postscript'),
        ('tool', 'builtin', 'task', 'nop', 'prescript'),
        ('tool', 'builtin', 'task', 'nop', 'script')}


def test_get_check_changed_keys_with_invalid_require(project):
    project.add("tool", "builtin", "task", "nop", "require", "this,key")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        with pytest.raises(KeyError, match=r"\[this,key\] not found"):
            node.get_check_changed_keys()


def test_get_check_changed_keys_with_require(project):
    project.add("tool", "builtin", "task", "nop", "require",
                "library,testdesign,fileset,rtl,idir")
    project.add("tool", "builtin", "task", "nop", "require",
                "library,testdesign,fileset,rtl,param,N")
    project.set("tool", "builtin", "task", "nop", "env", "BUILD", "this")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        values, paths = node.get_check_changed_keys()
    assert values == {
        ('library', 'testdesign', 'fileset', 'rtl', 'param', 'N'),
        ('tool', 'builtin', 'task', 'nop', 'env', "BUILD"),
        ('tool', 'builtin', 'task', 'nop', 'threads'),
        ('tool', 'builtin', 'task', 'nop', 'option')
    }
    assert paths == {
        ('library', 'testdesign', 'fileset', 'rtl', 'idir'),
        ('tool', 'builtin', 'task', 'nop', 'refdir'),
        ('tool', 'builtin', 'task', 'nop', 'postscript'),
        ('tool', 'builtin', 'task', 'nop', 'prescript'),
        ('tool', 'builtin', 'task', 'nop', 'script')
    }


def test_check_values_changed_no_change(project):
    project.set('library', 'testdesign', 'fileset', 'rtl', 'param', 'N', "64")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        assert node.check_values_changed(
            node, [('library', 'testdesign', 'fileset', 'rtl', 'param', 'N')]) is False


def test_check_values_changed_change(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    project.set('library', 'testdesign', 'fileset', 'rtl', 'param', 'N', "64")

    node = SchedulerNode(project, "steptwo", "0")

    other_project = project.copy()
    other_project.set('library', 'testdesign', 'fileset', 'rtl', 'param', 'N', "128")
    other = SchedulerNode(other_project, "steptwo", "0")

    with node.runtime(), other.runtime():
        assert node.check_values_changed(
            other, [('library', 'testdesign', 'fileset', 'rtl', 'param', 'N')]) is True
    assert "[library,testdesign,fileset,rtl,param,N] in steptwo/0 has been modified from " \
        "previous run" in caplog.text


def test_check_values_changed_change_missing(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        assert node.check_values_changed(node, [("option", "params", "N")]) is True
    assert "[option,params,N] in steptwo/0 has been modified from previous run" in caplog.text


def test_check_previous_run_status_flow(project):
    node = SchedulerNode(project, "steptwo", "0")
    flow = Flowgraph("testflow0")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    project = Project(project.design)
    project.set_flow(flow)
    project.add_fileset("rtl")
    node_other = SchedulerNode(project, "steptwo", "0")
    with node.runtime(), node_other.runtime():
        with pytest.raises(SchedulerFlowReset,
                           match=r"^Flow name changed, require full reset$"):
            node.check_previous_run_status(node_other)


def test_check_previous_run_status_tool(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.DEBUG)
    node = SchedulerNode(project, "steptwo", "0")
    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", EchoTask())
    flow.edge("stepone", "steptwo")
    project = Project(project.design)
    project.set_flow(flow)
    project.add_fileset("rtl")
    node_other = SchedulerNode(project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        assert node.check_previous_run_status(node_other) is False
    assert "Tool name changed" in caplog.text


def test_check_previous_run_status_task(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.DEBUG)
    node = SchedulerNode(project, "steptwo", "0")

    flow = Flowgraph("testflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", JoinTask())
    flow.edge("stepone", "steptwo")
    project = Project(project.design)
    project.set_flow(flow)
    project.add_fileset("rtl")

    node_other = SchedulerNode(project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        assert node.check_previous_run_status(node_other) is False
    assert "Task name changed" in caplog.text


def test_check_previous_run_status_running(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.DEBUG)
    project.set("record", "status", NodeStatus.RUNNING, step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        assert node.check_previous_run_status(node) is False
    assert "Previous step did not complete" in caplog.text


def test_check_previous_run_status_failed(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.DEBUG)
    project.set("record", "status", NodeStatus.ERROR, step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        assert node.check_previous_run_status(node) is False
    assert "Previous step was not successful" in caplog.text


def test_check_previous_run_status_inputs_changed(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)
    project.set("record", "status", NodeStatus.SUCCESS, step="steptwo", index="0")
    project.set("record", "inputnode", [("stepone", "0")], step="steptwo", index="0")

    def dummy_select(*_args, **_kwargs):
        return [("test", "1")]

    node = SchedulerNode(project, "steptwo", "0")
    monkeypatch.setattr(node.task, "select_input_nodes", dummy_select)

    with node.runtime():
        assert node.check_previous_run_status(node) is False
    assert "inputs to steptwo/0 has been modified from previous run" in caplog.text


def test_check_previous_run_status_no_change(project):
    project.set("record", "status", NodeStatus.SUCCESS, step="steptwo", index="0")
    project.set("record", "inputnode", [("stepone", "0")], step="steptwo", index="0")

    def dummy_select(*_args, **_kwargs):
        return [("stepone", "0")]

    node = SchedulerNode(project, "steptwo", "0")
    node.task.select_input_nodes = dummy_select

    with node.runtime():
        assert node.check_previous_run_status(node) is True


def test_check_files_changed_timestamp_no_change(project):
    with open("testfile.txt", "w") as f:
        f.write("test")

    now = time.time() + 1
    project.set("library", "testdesign", "fileset", "rtl", "file", "verilog", "testfile.txt")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        assert node.check_files_changed(
            node, now, [("library", "testdesign", "fileset", "rtl", "file", "verilog")]) is False


def test_check_files_changed_timestamp(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    now = time.time() - 1

    with open("testfile.txt", "w") as f:
        f.write("test")

    project.set("library", "testdesign", "fileset", "rtl", "file", "verilog", "testfile.txt")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        assert node.check_files_changed(
            node, now, [("library", "testdesign", "fileset", "rtl", "file", "verilog")]) is True
    assert "[library,testdesign,fileset,rtl,file,verilog] (timestamp) in steptwo/0 has been " \
        "modified from previous run" in caplog.text


# ... Rest of file remains unchanged until the next modifications ...

def test_run_pass_restore_env(project):
    node = SchedulerNode(project, "stepone", "0")
    node.task.setup_work_directory(node.workdir)
    node.task.set("env", "TEST", "THISVALUE")

    assert "TEST" not in os.environ

    def check_run(*_args, **_kwargs):
        assert "TEST" in os.environ
        assert "THISVALUE" == os.environ["TEST"]
        return 0

    with patch("siliconcompiler.Task.run_task") as run_task, \
         patch("siliconcompiler.scheduler.SchedulerNode.check_logfile") as check_logfile:
        run_task.side_effect = check_run
        node.run()
        check_logfile.assert_called_once()
        run_task.assert_called_once()

    assert "TEST" not in os.environ


# ... Later in file ...

def test_run_failed_to_execute_initial_save_has_error(project):
    node = SchedulerNode(project, "stepone", "0")
    node.task.setup_work_directory(node.workdir)

    assert node._SchedulerNode__generate_test_case is True

    with patch("siliconcompiler.Task.run_task") as run_task, \
         patch("siliconcompiler.scheduler.SchedulerNode.halt") as halt, \
         patch("siliconcompiler.scheduler.SchedulerNode._SchedulerNode__generate_testcase") as \
         testcase:
        run_task.return_value = 1

        def halt_step(*_args, **_kwargs):
            raise ValueError
        halt.side_effect = halt_step

        with pytest.raises(ValueError):
            node.run()

        run_task.assert_called_once()
        testcase.assert_called_once()

    assert project.get("record", "status", step="stepone", index="0") == NodeStatus.ERROR
    saved_manifest = Project.from_manifest(filepath=node.get_manifest())
    assert saved_manifest.get("record", "status", step="stepone", index="0") == NodeStatus.ERROR


# ... and ...

def test_run_with_queue(project):
    node = SchedulerNode(project, "stepone", "0")

    class DummyPipe:
        calls = 0

        def send(self, *_args, **_kwargs):
            self.calls += 1
    pipe = DummyPipe()
    node.set_queue(pipe, Queue())

    node.task.setup_work_directory(node.workdir)
    with patch("logging.Logger.removeHandler") as call_remove_logger, \
         patch("siliconcompiler.scheduler.SchedulerNode.execute") as call_exec:
        node.run()
        call_exec.assert_called_once()
        call_remove_logger.assert_called_once()
        assert pipe.calls == 1


def test_copy_from(project, monkeypatch, caplog, has_graphviz):
    _ = has_graphviz
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    node = SchedulerNode(project, "stepone", "0")
    with node.runtime():
        node.task.setup_work_directory(node.workdir)
        node.task.generate_replay_script(node.replay_script, node.workdir)
        project.write_manifest(node.get_manifest("input"))
        project.write_manifest(node.get_manifest("output"))

    project.set("option", "jobname", "newname")
    node = SchedulerNode(project, "stepone", "0")

    assert not os.path.exists(node.replay_script)
    assert not os.path.exists(node.get_manifest("input"))
    assert not os.path.exists(node.get_manifest("output"))

    node.copy_from("job0")
    assert "Importing stepone/0 from job0" in caplog.text

    assert os.path.exists(node.replay_script)
    with open(node.replay_script, "r") as f:
        assert "job0" not in f.read()

    assert os.path.exists(node.get_manifest("input"))
    input_schema = Project.from_manifest(filepath=node.get_manifest("input"))
    assert input_schema.get("option", "jobname") == "newname"

    assert os.path.exists(node.get_manifest("output"))
    output_schema = Project.from_manifest(filepath=node.get_manifest("output"))
    assert output_schema.get("option", "jobname") == "newname"


# SchedulerFlowReset exception tests

def test_scheduler_flow_reset_exception_can_be_raised():
    """Test that SchedulerFlowReset can be raised with a message"""
    from siliconcompiler.scheduler.schedulernode import SchedulerFlowReset

    with pytest.raises(SchedulerFlowReset) as excinfo:
        raise SchedulerFlowReset("Test flow reset")  # noqa
    assert str(excinfo.value) == "Test flow reset"


def test_scheduler_flow_reset_exception_can_be_caught():
    """Test that SchedulerFlowReset can be caught specifically"""
    from siliconcompiler.scheduler.schedulernode import SchedulerFlowReset

    with pytest.raises(SchedulerFlowReset):
        raise SchedulerFlowReset("Test message")  # noqa


def test_check_previous_run_status_flow_raises_scheduler_flow_reset(project):
    """Test that flow name change raises SchedulerFlowReset instead of returning False"""
    from siliconcompiler.scheduler.schedulernode import SchedulerFlowReset

    node = SchedulerNode(project, "steptwo", "0")

    # Create a different flow
    flow = Flowgraph("differentflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    other_project = Project(project.design)
    other_project.set_flow(flow)
    other_project.add_fileset("rtl")
    node_other = SchedulerNode(other_project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        with pytest.raises(SchedulerFlowReset):
            node.check_previous_run_status(node_other)


def test_check_previous_run_status_flow_reset_message(project):
    """Test that SchedulerFlowReset contains appropriate message"""
    from siliconcompiler.scheduler.schedulernode import SchedulerFlowReset

    node = SchedulerNode(project, "steptwo", "0")

    # Create a different flow
    flow = Flowgraph("differentflow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")
    other_project = Project(project.design)
    other_project.set_flow(flow)
    other_project.add_fileset("rtl")
    node_other = SchedulerNode(other_project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        try:
            node.check_previous_run_status(node_other)
            raise AssertionError("Should have raised SchedulerFlowReset")  # noqa
        except SchedulerFlowReset as e:
            assert "Flow name changed" in str(e)
            assert "require full reset" in str(e)


def test_check_previous_run_status_same_flow_doesnt_raise(project):
    """Test that same flow name doesn't raise SchedulerFlowReset"""
    node = SchedulerNode(project, "steptwo", "0")

    # Set up same flow with successful run
    project.set("record", "status", NodeStatus.SUCCESS, step="steptwo", index="0")
    project.set("record", "inputnode", [("stepone", "0")], step="steptwo", index="0")

    def dummy_select(*_args, **_kwargs):
        return [("stepone", "0")]

    import unittest.mock
    with unittest.mock.patch.object(node.task, 'select_input_nodes', dummy_select):
        with node.runtime():
            # Should not raise SchedulerFlowReset
            result = node.check_previous_run_status(node)
            assert result is True


def test_requires_run_can_raise_scheduler_flow_reset(project):
    """Test that requires_run can propagate SchedulerFlowReset"""
    from siliconcompiler.scheduler.schedulernode import SchedulerFlowReset

    node = SchedulerNode(project, "steptwo", "0")

    # Create manifests that will trigger check_previous_run_status
    os.makedirs(os.path.dirname(node.get_manifest(input=True)))
    project.write_manifest(node.get_manifest(input=True))
    os.makedirs(os.path.dirname(node.get_manifest()))
    project.write_manifest(node.get_manifest())

    # Mock check_previous_run_status to raise SchedulerFlowReset
    def mock_check(*_args):
        raise SchedulerFlowReset("Test reset")  # noqa

    import unittest.mock
    with unittest.mock.patch.object(node, 'check_previous_run_status', mock_check):
        # requires_run should propagate the exception
        with pytest.raises(SchedulerFlowReset):
            node.requires_run()