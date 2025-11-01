import logging
import os
import pytest
import re
import shutil
import time

import os.path

from pathlib import Path
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
from siliconcompiler.scheduler.schedulernode import SchedulerFlowReset, \
    SchedulerNodeReset, SchedulerNodeResetSilent
from siliconcompiler.utils.paths import jobdir, workdir


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
    with pytest.raises(TypeError, match="^step must be a string with a value$"):
        SchedulerNode(project, None, "0")


def test_init_invalid_step_empty(project):
    with pytest.raises(TypeError, match="^step must be a string with a value$"):
        SchedulerNode(project, "", "0")


def test_init_invalid_index(project):
    with pytest.raises(TypeError, match="^index must be a string with a value$"):
        SchedulerNode(project, "step", None)


def test_init_invalid_index_int(project):
    with pytest.raises(TypeError, match="^index must be a string with a value$"):
        SchedulerNode(project, "step", 0)


def test_init_invalid_index_empty(project):
    with pytest.raises(TypeError, match="^index must be a string with a value$"):
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
    with pytest.raises(ValueError, match="^invalid is not a log$"):
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

    def dummy_setup(*args, **kwargs):
        raise ValueError("Find this")
    monkeypatch.setattr(node.task, "setup", dummy_setup)

    with node.runtime():
        with pytest.raises(ValueError, match="^Find this$"):
            node.setup()
    assert "Failed to run setup() for steptwo/0 with builtin/nop" in caplog.text


def test_setup_with_return(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    node = SchedulerNode(project, "steptwo", "0")

    def dummy_setup(*args, **kwargs):
        return "This should not be there"
    monkeypatch.setattr(node.task, "setup", dummy_setup)

    with node.runtime():
        with pytest.raises(RuntimeError,
                           match=r"^setup\(\) returned a value, but should not have: "
                           "This should not be there$"):
            node.setup()
    assert "Failed to run setup() for steptwo/0 with builtin/nop" in caplog.text


def test_setup_skipped(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    node = SchedulerNode(project, "steptwo", "0")

    def dummy_setup(*args, **kwargs):
        raise TaskSkip("skip me")
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
        with pytest.raises(KeyError, match="^'\\[this,key\\] not found'$"):
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
        node.check_values_changed(
            node, [('library', 'testdesign', 'fileset', 'rtl', 'param', 'N')])


def test_check_values_changed_change(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    project.set('library', 'testdesign', 'fileset', 'rtl', 'param', 'N', "64")

    node = SchedulerNode(project, "steptwo", "0")

    other_project = project.copy()
    other_project.set('library', 'testdesign', 'fileset', 'rtl', 'param', 'N', "128")
    other = SchedulerNode(other_project, "steptwo", "0")

    with node.runtime(), other.runtime():
        with pytest.raises(SchedulerNodeReset,
                           match=r"^\[library,testdesign,fileset,rtl,param,N\] in steptwo/0 "
                                 r"has been modified from previous run$"):
            node.check_values_changed(
                other, [('library', 'testdesign', 'fileset', 'rtl', 'param', 'N')])


def test_check_values_changed_change_missing(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        with pytest.raises(SchedulerNodeReset,
                           match=r"^\[option,params,N\] in steptwo/0 has been modified "
                                 r"from previous run$"):
            node.check_values_changed(node, [("option", "params", "N")])


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


def test_check_previous_run_status_tool(project):
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
        with pytest.raises(SchedulerNodeResetSilent,
                           match=r"^Tool name changed$"):
            node.check_previous_run_status(node_other)


def test_check_previous_run_status_task(project):
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
        with pytest.raises(SchedulerNodeResetSilent,
                           match=r"^Task name changed$"):
            node.check_previous_run_status(node_other)


def test_check_previous_run_status_running(project):
    project.set("record", "status", NodeStatus.RUNNING, step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        with pytest.raises(SchedulerNodeResetSilent,
                           match=r"^Previous step did not complete$"):
            node.check_previous_run_status(node)


def test_check_previous_run_status_failed(project):
    project.set("record", "status", NodeStatus.ERROR, step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        with pytest.raises(SchedulerNodeResetSilent,
                           match=r"^Previous step was not successful$"):
            node.check_previous_run_status(node)


def test_check_previous_run_status_inputs_changed(project, monkeypatch):
    project.set("record", "status", NodeStatus.SUCCESS, step="steptwo", index="0")
    project.set("record", "inputnode", [("stepone", "0")], step="steptwo", index="0")

    def dummy_select(*args, **kwargs):
        return [("test", "1")]

    node = SchedulerNode(project, "steptwo", "0")
    monkeypatch.setattr(node.task, "select_input_nodes", dummy_select)

    with node.runtime():
        with pytest.raises(SchedulerNodeReset,
                           match=r"^inputs to steptwo/0 has been modified from previous run$"):
            node.check_previous_run_status(node)


def test_check_previous_run_status_no_change(project, monkeypatch):
    node = SchedulerNode(project, "steptwo", "0")
    project.set("record", "status", NodeStatus.SUCCESS, step="steptwo", index="0")
    project.set("record", "inputnode", [("stepone", "0")], step="steptwo", index="0")

    def dummy_select(*args, **kwargs):
        return [("stepone", "0")]
    monkeypatch.setattr(node.task, "select_input_nodes", dummy_select)

    with node.runtime():
        node.check_previous_run_status(node)


def test_check_files_changed_timestamp_no_change(project):
    with open("testfile.txt", "w") as f:
        f.write("test")

    now = time.time() + 1
    project.set("library", "testdesign", "fileset", "rtl", "file", "verilog", "testfile.txt")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        node.check_files_changed(
            node, now, [("library", "testdesign", "fileset", "rtl", "file", "verilog")])


def test_check_files_changed_timestamp(project):
    now = time.time() - 1

    with open("testfile.txt", "w") as f:
        f.write("test")

    project.set("library", "testdesign", "fileset", "rtl", "file", "verilog", "testfile.txt")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        with pytest.raises(SchedulerNodeReset,
                           match=r"^\[library,testdesign,fileset,rtl,file,verilog\] \(timestamp\) "
                                 r"in steptwo/0 has been modified from previous run$"):
            node.check_files_changed(
                node, now, [("library", "testdesign", "fileset", "rtl", "file", "verilog")])


def test_check_files_changed_directory(project):
    os.makedirs("testdir", exist_ok=True)

    with open("testdir/testfile.txt", "w") as f:
        f.write("test")

    now = time.time() + 1

    project.set("library", "testdesign", "fileset", "rtl", "idir", "testdir")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        node.check_files_changed(
            node, now, [("library", "testdesign", "fileset", "rtl", "idir")])


def test_check_files_changed_timestamp_directory(project):
    now = time.time() - 1

    os.makedirs("testdir", exist_ok=True)

    with open("testdir/testfile.txt", "w") as f:
        f.write("test")

    project.set("library", "testdesign", "fileset", "rtl", "idir", "testdir")
    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        with pytest.raises(SchedulerNodeReset,
                           match=r"^\[library,testdesign,fileset,rtl,idir\] \(timestamp\) "
                                 r"in steptwo/0 has been modified from previous run$"):
            node.check_files_changed(
                node, now, [("library", "testdesign", "fileset", "rtl", "idir")])


def test_check_files_changed_package(project):
    now = time.time() - 1

    with open("testfile.txt", "w") as f:
        f.write("test")

    node = SchedulerNode(project, "steptwo", "0")
    project.set("library", "testdesign", "fileset", "rtl", "file", "verilog", "testfile.txt")

    node_other = SchedulerNode(project.copy(), "steptwo", "0")

    project.design.set_dataroot("testing", "file://.")
    with project.design.active_dataroot("testing"):
        project.design.set("fileset", "rtl", "file", "verilog", "testfile.txt")

    with node.runtime(), node_other.runtime():
        with pytest.raises(SchedulerNodeReset,
                           match=r"^\[library,testdesign,fileset,rtl,file,verilog\] \(file "
                                 r"dataroot\) in steptwo/0 has been modified from previous run$"):
            node.check_files_changed(
                node_other, now,
                [("library", "testdesign", "fileset", "rtl", "file", "verilog")])


def test_check_files_changed_timestamp_current_hash(project):
    now = time.time() - 1

    with open("testfile.txt", "w") as f:
        f.write("test")

    project.set("library", "testdesign", "fileset", "rtl", "file", "verilog", "testfile.txt")

    node_other = SchedulerNode(project.copy(), "steptwo", "0")

    project.set("option", "hash", True)
    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime(), node_other.runtime():
        with pytest.raises(SchedulerNodeReset,
                           match=r"^\[library,testdesign,fileset,rtl,file,verilog\] \(timestamp\) "
                                 r"in steptwo/0 has been modified from previous run$"):
            node.check_files_changed(
                node_other, now,
                [("library", "testdesign", "fileset", "rtl", "file", "verilog")])


def test_check_files_changed_timestamp_previous_hash(project):
    now = time.time() - 1

    with open("testfile.txt", "w") as f:
        f.write("test")

    project.set("library", "testdesign", "fileset", "rtl", "file", "verilog", "testfile.txt")

    node = SchedulerNode(project, "steptwo", "0")
    project = project.copy()
    project.set("option", "hash", True)
    node_other = SchedulerNode(project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        with pytest.raises(SchedulerNodeReset,
                           match=r"^\[library,testdesign,fileset,rtl,file,verilog\] \(timestamp\) "
                                 r"in steptwo/0 has been modified from previous run$"):
            node.check_files_changed(
                node_other, now,
                [("library", "testdesign", "fileset", "rtl", "file", "verilog")])


def test_check_files_changed_hash_no_change(project):
    now = time.time() - 1

    with open("testfile.txt", "w") as f:
        f.write("test")

    project.set("option", "hash", True)
    project.set("library", "testdesign", "fileset", "rtl", "file", "verilog", "testfile.txt")
    other_project = project.copy()

    project.hash_files("library", "testdesign", "fileset", "rtl", "idir")

    node = SchedulerNode(project, "steptwo", "0")
    node_other = SchedulerNode(other_project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        node.check_files_changed(
            node_other, now, [("library", "testdesign", "fileset", "rtl", "idir")])


def test_check_files_changed_hash_directory(project):
    now = time.time() - 1

    os.makedirs("testdir", exist_ok=True)

    with open("testdir/testfile.txt", "w") as f:
        f.write("test")

    project.set("option", "hash", True)
    project.set("library", "testdesign", "fileset", "rtl", "idir", "testdir")
    other_project = project.copy()

    project.hash_files("library", "testdesign", "fileset", "rtl", "idir")

    with open("testdir/testfile.txt", "w") as f:
        f.write("testing")

    node = SchedulerNode(project, "steptwo", "0")
    node_other = SchedulerNode(other_project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        with pytest.raises(SchedulerNodeReset,
                           match=r"^\[library,testdesign,fileset,rtl,idir\] \(file hash\) "
                                 r"in steptwo/0 has been modified from previous run$"):
            node.check_files_changed(
                node_other, now, [("library", "testdesign", "fileset", "rtl", "idir")])


def test_requires_run_breakpoint(project):
    assert project.set("option", "breakpoint", True, step="steptwo")

    node = SchedulerNode(project, "steptwo", "0")

    with pytest.raises(SchedulerNodeResetSilent,
                       match=r"^Breakpoint is set on steptwo/0$"):
        node.requires_run()


def test_requires_run_fail_input(project):
    node = SchedulerNode(project, "steptwo", "0")

    with pytest.raises(SchedulerNodeResetSilent,
                       match=r"^Previous run did not generate input manifest$"):
        node.requires_run()


def test_requires_run_fail_output(project):
    node = SchedulerNode(project, "steptwo", "0")

    os.makedirs(os.path.dirname(node.get_manifest(input=True)))
    project.write_manifest(node.get_manifest(input=True))

    with pytest.raises(SchedulerNodeResetSilent,
                       match=r"^Previous run did not generate output manifest$"):
        node.requires_run()


def test_requires_run_all_pass(project, monkeypatch):
    node = SchedulerNode(project, "steptwo", "0")

    os.makedirs(os.path.dirname(node.get_manifest(input=True)))
    project.write_manifest(node.get_manifest(input=True))
    os.makedirs(os.path.dirname(node.get_manifest()))
    project.write_manifest(node.get_manifest())

    def dummy_get_check_changed_keys(*args):
        return (set(), set())
    monkeypatch.setattr(node, "get_check_changed_keys", dummy_get_check_changed_keys)

    def dummy_check_previous_run_status(*args):
        return True
    monkeypatch.setattr(node, "check_previous_run_status", dummy_check_previous_run_status)

    node.requires_run()


def test_requires_run_all_input_corrupt(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.DEBUG)

    node = SchedulerNode(project, "steptwo", "0")

    os.makedirs(os.path.dirname(node.get_manifest(input=True)))
    with open(node.get_manifest(input=True), "w") as f:
        f.write("this is not a json file")

    with pytest.raises(SchedulerNodeResetSilent,
                       match=r"^Input manifest failed to load$"):
        node.requires_run()


def test_requires_run_all_output_corrupt(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.DEBUG)

    node = SchedulerNode(project, "steptwo", "0")

    os.makedirs(os.path.dirname(node.get_manifest(input=True)))
    project.write_manifest(node.get_manifest(input=True))

    os.makedirs(os.path.dirname(node.get_manifest()))
    with open(node.get_manifest(), "w") as f:
        f.write("this is not a json file")

    with pytest.raises(SchedulerNodeResetSilent,
                       match=r"^Output manifest failed to load$"):
        node.requires_run()


def test_requires_run_all_keys_failed(project, monkeypatch):
    node = SchedulerNode(project, "steptwo", "0")

    os.makedirs(os.path.dirname(node.get_manifest(input=True)))
    project.write_manifest(node.get_manifest(input=True))
    os.makedirs(os.path.dirname(node.get_manifest()))
    project.write_manifest(node.get_manifest())

    def dummy_check_previous_run_status(*args):
        return True
    monkeypatch.setattr(node, "check_previous_run_status", dummy_check_previous_run_status)

    def dummy_get_check_changed_keys(*args):
        raise KeyError
    monkeypatch.setattr(node, "get_check_changed_keys", dummy_get_check_changed_keys)

    with pytest.raises(SchedulerNodeResetSilent, match=r"^Failed to acquire keys$"):
        node.requires_run()


def test_check_logfile(project, datadir, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    # add regex
    project.add('tool', 'builtin', 'task', 'nop', 'regex', 'errors', "ERROR")
    project.add('tool', 'builtin', 'task', 'nop', 'regex', 'warnings', "WARNING")
    project.add('tool', 'builtin', 'task', 'nop', 'regex', 'warnings', "-v DPL")

    node = SchedulerNode(project, "stepone", "0")
    assert project.get("metric", "errors", step="stepone", index="0") is None
    assert project.get("metric", "warnings", step="stepone", index="0") is None

    with node.runtime():
        # check log
        os.makedirs(node.workdir, exist_ok=True)
        shutil.copy(os.path.join(datadir, 'schedulernode', 'check_logfile.log'),
                    node.get_log())
        node.check_logfile()

    # check line numbers in log and file
    warning_with_line_number = ' 90: [WARNING GRT-0043] No OR_DEFAULT vias defined.'
    error_with_line_number = ' 5: [ERROR XYZ-123] Test error'
    assert re.search(re.escape(warning_with_line_number)+r'\n.*'+re.escape(error_with_line_number),
                     caplog.text)

    errors_file = "stepone.errors"
    assert os.path.isfile(errors_file)
    with open(errors_file) as file:
        assert error_with_line_number in file.read()

    warnings_file = "stepone.warnings"
    assert os.path.isfile(warnings_file)
    with open(warnings_file) as file:
        assert warning_with_line_number in file.read()

    assert project.get("metric", "errors", step="stepone", index="0") == 1
    assert project.get("metric", "warnings", step="stepone", index="0") == 1


def test_check_logfile_with_extra_metrics(project, datadir, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    # add regex
    project.add('tool', 'builtin', 'task', 'nop', 'regex', 'errors', "ERROR")
    project.add('tool', 'builtin', 'task', 'nop', 'regex', 'warnings', "WARNING")
    project.add('tool', 'builtin', 'task', 'nop', 'regex', 'warnings', "-v DPL")

    node = SchedulerNode(project, "stepone", "0")
    assert project.get("metric", "errors", step="stepone", index="0") is None
    assert project.get("metric", "warnings", step="stepone", index="0") is None
    project.set("metric", "errors", 5, step="stepone", index="0")
    project.set("metric", "warnings", 11, step="stepone", index="0")

    with node.runtime():
        # check log
        os.makedirs(node.workdir, exist_ok=True)
        shutil.copy(os.path.join(datadir, 'schedulernode', 'check_logfile.log'),
                    node.get_log())
        node.check_logfile()

    # check line numbers in log and file
    warning_with_line_number = ' 90: [WARNING GRT-0043] No OR_DEFAULT vias defined.'
    error_with_line_number = ' 5: [ERROR XYZ-123] Test error'
    assert re.search(re.escape(warning_with_line_number)+r'\n.*'+re.escape(error_with_line_number),
                     caplog.text)

    errors_file = "stepone.errors"
    assert os.path.isfile(errors_file)
    with open(errors_file) as file:
        assert error_with_line_number in file.read()

    warnings_file = "stepone.warnings"
    assert os.path.isfile(warnings_file)
    with open(warnings_file) as file:
        assert warning_with_line_number in file.read()

    assert project.get("metric", "errors", step="stepone", index="0") == 6
    assert project.get("metric", "warnings", step="stepone", index="0") == 12


def test_check_logfile_none(project, datadir):
    node = SchedulerNode(project, "stepone", "0")
    assert project.get("metric", "errors", step="stepone", index="0") is None
    assert project.get("metric", "warnings", step="stepone", index="0") is None

    with node.runtime():
        # check log
        os.makedirs(node.workdir, exist_ok=True)
        shutil.copy(os.path.join(datadir, 'schedulernode', 'check_logfile.log'),
                    node.get_log())
        node.check_logfile()

    errors_file = "stepone.errors"
    assert not os.path.isfile(errors_file)

    warnings_file = "stepone.warnings"
    assert not os.path.isfile(warnings_file)

    assert project.get("metric", "errors", step="stepone", index="0") is None
    assert project.get("metric", "warnings", step="stepone", index="0") is None


def test_check_logfile_non_metric(project, datadir):
    # add regex
    project.add('tool', 'builtin', 'task', 'nop', 'regex', 'somethingelse', "ERROR")

    node = SchedulerNode(project, "stepone", "0")
    assert project.get("metric", "errors", step="stepone", index="0") is None
    assert project.get("metric", "warnings", step="stepone", index="0") is None

    with node.runtime():
        # check log
        os.makedirs(node.workdir, exist_ok=True)
        shutil.copy(os.path.join(datadir, 'schedulernode', 'check_logfile.log'),
                    node.get_log())
        node.check_logfile()

    assert os.path.isfile("stepone.somethingelse")

    assert project.get("metric", "errors", step="stepone", index="0") is None
    assert project.get("metric", "warnings", step="stepone", index="0") is None


def test_setup_input_directory_do_nothing(project):
    node = SchedulerNode(project, "stepone", "0")
    with node.runtime():
        node.setup_input_directory()


def test_setup_input_directory(project):
    output_dir = Path(workdir(project, step="stepone", index="0")) / "outputs"
    input_dir = Path(workdir(project, step="steptwo", index="0")) / "inputs"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(input_dir, exist_ok=True)

    jsonfile = output_dir / "dummy.pkg.json"
    jsonfile.touch()
    file0 = output_dir / "file0.txt"
    file0.touch()
    file1 = output_dir / "file1.txt"
    file1.touch()

    project.set("record", "inputnode", ("stepone", "0"), step="steptwo", index="0")
    project.set("tool", "builtin", "task", "nop", "input", "file0.txt", step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        node.setup_input_directory()

    assert os.path.isfile(input_dir / "file0.txt")
    assert not os.path.isfile(input_dir / "file1.txt")
    assert not os.path.isfile(input_dir / "dummy.pkg.json")


def test_setup_input_directory_directory(project):
    output_dir = Path(workdir(project, step="stepone", index="0")) / "outputs"
    input_dir = Path(workdir(project, step="steptwo", index="0")) / "inputs"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(input_dir, exist_ok=True)

    jsonfile = output_dir / "dummy.pkg.json"
    jsonfile.touch()
    dir0 = output_dir / "dir0"
    dir0.mkdir(exist_ok=True)

    project.set("record", "inputnode", ("stepone", "0"), step="steptwo", index="0")
    project.set("tool", "builtin", "task", "nop", "input", "dir0", step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        node.setup_input_directory()

    assert os.path.isdir(input_dir / "dir0")
    assert not os.path.isfile(input_dir / "dummy.pkg.json")


def test_setup_input_directory_renames_dir(project):
    output_dir = Path(workdir(project, step="stepone", index="0")) / "outputs"
    input_dir = Path(workdir(project, step="steptwo", index="0")) / "inputs"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(input_dir, exist_ok=True)

    jsonfile = output_dir / "dummy.pkg.json"
    jsonfile.touch()
    dir0 = output_dir / "dir0"
    dir0.mkdir(exist_ok=True)

    project.set("record", "inputnode", ("stepone", "0"), step="steptwo", index="0")
    project.set("tool", "builtin", "task", "nop", "input", "dir0.stepone0",
                step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        node.setup_input_directory()

    assert not os.path.exists(input_dir / "dir0")
    assert os.path.isdir(input_dir / "dir0.stepone0")
    assert not os.path.isfile(input_dir / "dummy.pkg.json")


def test_setup_input_directory_renames_file(project):
    output_dir = Path(workdir(project, step="stepone", index="0")) / "outputs"
    input_dir = Path(workdir(project, step="steptwo", index="0")) / "inputs"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(input_dir, exist_ok=True)

    jsonfile = output_dir / "dummy.pkg.json"
    jsonfile.touch()
    file0 = output_dir / "file0.txt"
    file0.touch()
    file1 = output_dir / "file1.txt"
    file1.touch()

    project.set("record", "inputnode", ("stepone", "0"), step="steptwo", index="0")
    project.set("tool", "builtin", "task", "nop", "input", "file0.stepone0.txt",
                step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        node.setup_input_directory()

    assert not os.path.exists(input_dir / "file0.txt")
    assert os.path.isfile(input_dir / "file0.stepone0.txt")
    assert not os.path.isfile(input_dir / "dummy.pkg.json")


def test_setup_input_directory_no_input_dir(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())

    input_dir = Path(workdir(project, step="steptwo", index="0")) / "inputs"
    os.makedirs(input_dir, exist_ok=True)
    output_dir = Path(workdir(project, step="steptwo", index="0")) / "outputs"
    os.makedirs(output_dir, exist_ok=True)

    project.set("record", "inputnode", ("stepone", "0"), step="steptwo", index="0")
    project.set("tool", "builtin", "task", "nop", "input", "file0.txt",
                step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        with pytest.raises(SystemExit):
            node.setup_input_directory()

    assert "Unable to locate outputs directory for stepone/0: " in caplog.text


@pytest.mark.parametrize("error", [NodeStatus.ERROR, NodeStatus.TIMEOUT])
def test_setup_input_directory_input_error(project, error, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())

    input_dir = Path(workdir(project, step="steptwo", index="0")) / "inputs"
    os.makedirs(input_dir, exist_ok=True)
    output_dir = Path(workdir(project, step="steptwo", index="0")) / "outputs"
    os.makedirs(output_dir, exist_ok=True)

    project.set("record", "status", error, step="stepone", index="0")
    project.set("record", "inputnode", ("stepone", "0"), step="steptwo", index="0")
    project.set("tool", "builtin", "task", "nop", "input", "file0.txt",
                step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        with pytest.raises(SystemExit):
            node.setup_input_directory()

    assert "Halting steptwo/0 due to errors" in caplog.text


def test_validate(project):
    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        assert node.validate() is True


def test_validate_missing_inputs(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())

    project.set("tool", "builtin", "task", "nop", "input", "file0.txt",
                step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        assert node.validate() is False
    assert "Required input file0.txt not received for steptwo/0" in caplog.text


def test_validate_missing_required_key(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())

    project.set("tool", "builtin", "task", "nop", "require", ["key,not,found"],
                step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        assert node.validate() is False
    assert "Cannot resolve required keypath [key,not,found]" in caplog.text


def test_validate_empty_required_key(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())

    project.set("tool", "builtin", "task", "nop", "require",
                ["library,testdesign,fileset,rtl,topmodule"],
                step="steptwo", index="0")
    project.unset("library", "testdesign", "fileset", "rtl", "topmodule")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        assert node.validate() is False
    assert "No value set for required keypath [library,testdesign,fileset,rtl,topmodule]" \
        in caplog.text


def test_validate_missing_required_file(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())

    project.set("tool", "builtin", "task", "nop", "require",
                ["library,testdesign,fileset,rtl,file,verilog"],
                step="steptwo", index="0")
    project.set("library", "testdesign", "fileset", "rtl", "file", "verilog", "test.txt")

    node = SchedulerNode(project, "steptwo", "0")
    with node.runtime():
        assert node.validate() is False
    assert "Cannot resolve path test.txt in required file keypath " \
        "[library,testdesign,fileset,rtl,file,verilog]" in caplog.text


def test_summarize(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    project.set("metric", "errors", 2, step="steptwo", index="0")
    project.set("metric", "warnings", 4, step="steptwo", index="0")
    project.set("metric", "tasktime", 12.5, step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")
    node.summarize()
    assert "Number of errors: 2\n" in caplog.text
    assert "Number of warnings: 4\n" in caplog.text
    assert "Finished task in 12.50s\n" in caplog.text


def test_report_output_files_builtin(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    node = SchedulerNode(project, "steptwo", "0")
    node.set_builtin()
    with node.runtime():
        node._SchedulerNode__report_output_files()
    assert caplog.text == ""


def test_report_output_files_missing_outputs_dir(echo_project, monkeypatch, caplog):
    monkeypatch.setattr(echo_project, "_Project__logger", logging.getLogger())
    node = SchedulerNode(echo_project, "steptwo", "0")
    with node.runtime():
        with pytest.raises(SystemExit):
            node._SchedulerNode__report_output_files()
    assert "Output directory is missing" in caplog.text
    assert "Failed to write manifest for steptwo/0" in caplog.text
    assert "Halting steptwo/0 due to errors" in caplog.text


def test_report_output_files_missing_manifest(echo_project, monkeypatch, caplog):
    monkeypatch.setattr(echo_project, "_Project__logger", logging.getLogger())
    node = SchedulerNode(echo_project, "steptwo", "0")
    with node.runtime():
        os.makedirs(os.path.join(node.workdir, "outputs"), exist_ok=True)

        with pytest.raises(SystemExit):
            node._SchedulerNode__report_output_files()
    assert "Output manifest (testdesign.pkg.json) is missing." in caplog.text
    assert "Halting steptwo/0 due to errors" in caplog.text


def test_report_output_files_missing_outputs(echo_project, monkeypatch, caplog):
    monkeypatch.setattr(echo_project, "_Project__logger", logging.getLogger())
    echo_project.set("tool", "echo", "task", "echo", "output", "echothis.txt",
                     step="steptwo", index="0")

    node = SchedulerNode(echo_project, "steptwo", "0")
    with node.runtime():
        os.makedirs(os.path.join(node.workdir, "outputs"), exist_ok=True)
        echo_project.write_manifest(node.get_manifest())

        with pytest.raises(SystemExit):
            node._SchedulerNode__report_output_files()
    assert "Expected output files are missing: echothis.txt" in caplog.text
    assert "Halting steptwo/0 due to errors" in caplog.text


def test_report_output_files_extra_outputs(echo_project, monkeypatch, caplog):
    monkeypatch.setattr(echo_project, "_Project__logger", logging.getLogger())
    echo_project.set("tool", "echo", "task", "echo", "output", "echothis.txt",
                     step="steptwo", index="0")

    node = SchedulerNode(echo_project, "steptwo", "0")
    with node.runtime():
        os.makedirs(os.path.join(node.workdir, "outputs"), exist_ok=True)
        echo_project.write_manifest(node.get_manifest())

        with open(os.path.join(node.workdir, "outputs", "echothis.txt"), 'w') as f:
            f.write("test")
        with open(os.path.join(node.workdir, "outputs", "extra.txt"), 'w') as f:
            f.write("test")

        with pytest.raises(SystemExit):
            node._SchedulerNode__report_output_files()
    assert "Unexpected output files found: extra.txt" in caplog.text
    assert "Halting steptwo/0 due to errors" in caplog.text


def test_run_pass(project):
    node = SchedulerNode(project, "stepone", "0")
    node.task.setup_work_directory(node.workdir)
    with patch("siliconcompiler.schema_support.record.RecordSchema.record_userinformation") \
            as call_track, \
         patch("siliconcompiler.schema_support.record.RecordSchema.record_version") \
            as call_version, \
         patch("siliconcompiler.schema_support.pathschema.PathSchemaBase.hash_files") as call_hash:
        node.run()
        call_track.assert_not_called()
        call_version.assert_called_once()
        call_hash.assert_not_called()

    assert project.get("metric", "tasktime", step="stepone", index="0") is not None
    assert project.get("metric", "totaltime", step="stepone", index="0") is not None
    assert project.get("record", "status", step="stepone", index="0") == NodeStatus.SUCCESS


def test_run_pass_record(project):
    project.set("option", "track", True)

    node = SchedulerNode(project, "stepone", "0")
    node.task.setup_work_directory(node.workdir)

    with patch("siliconcompiler.schema_support.record.RecordSchema.record_userinformation") \
            as call_track, \
         patch("siliconcompiler.schema_support.record.RecordSchema.record_version") \
            as call_version, \
         patch("siliconcompiler.schema_support.pathschema.PathSchemaBase.hash_files") as call_hash:
        node.run()
        call_track.assert_called_once()
        call_version.assert_called_once()
        call_hash.assert_not_called()

    assert project.get("metric", "tasktime", step="stepone", index="0") is not None
    assert project.get("metric", "totaltime", step="stepone", index="0") is not None
    assert project.get("record", "status", step="stepone", index="0") == NodeStatus.SUCCESS


def test_run_pass_restore_env(project):
    node = SchedulerNode(project, "stepone", "0")
    node.task.setup_work_directory(node.workdir)
    node.task.set("env", "TEST", "THISVALUE")

    assert "TEST" not in os.environ

    def check_run(*args, **kwargs):
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


def test_run_pass_hash(project):
    project.set("option", "hash", True)

    node = SchedulerNode(project, "stepone", "0")
    node.task.setup_work_directory(node.workdir)

    with patch("siliconcompiler.schema_support.record.RecordSchema.record_userinformation") \
            as call_track, \
         patch("siliconcompiler.schema_support.record.RecordSchema.record_version") \
            as call_version, \
         patch("siliconcompiler.schema_support.pathschema.PathSchemaBase.hash_files") as call_hash:
        node.run()
        call_track.assert_not_called()
        call_version.assert_called_once()
        call_hash.assert_called()

    assert project.get("metric", "tasktime", step="stepone", index="0") is not None
    assert project.get("metric", "totaltime", step="stepone", index="0") is not None
    assert project.get("record", "status", step="stepone", index="0") == NodeStatus.SUCCESS


def test_run_failed_to_validate(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    node = SchedulerNode(project, "stepone", "0")
    node.task.setup_work_directory(node.workdir)

    with patch("siliconcompiler.scheduler.SchedulerNode.validate") as call_validate:
        call_validate.return_value = False
        with pytest.raises(SystemExit):
            node.run()
        call_validate.assert_called_once()

    assert project.get("metric", "tasktime", step="stepone", index="0") is None
    assert project.get("metric", "totaltime", step="stepone", index="0") is None
    assert project.get("record", "status", step="stepone", index="0") == NodeStatus.ERROR

    assert "Failed to validate node setup. See previous errors" in caplog.text
    assert "Halting stepone/0 due to errors" in caplog.text


def test_run_failed_select_input(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    node = SchedulerNode(project, "steptwo", "0")
    node.task.setup_work_directory(node.workdir)

    with patch("siliconcompiler.Task.select_input_nodes") as call_input_select:
        call_input_select.return_value = []
        with pytest.raises(SystemExit):
            node.run()
        call_input_select.assert_called_once()

    assert project.get("metric", "tasktime", step="steptwo", index="0") is None
    assert project.get("metric", "totaltime", step="steptwo", index="0") is None
    assert project.get("record", "status", step="steptwo", index="0") == NodeStatus.ERROR

    assert "No inputs selected for steptwo/0" in caplog.text
    assert "Halting steptwo/0 due to errors" in caplog.text


def test_run_failed_to_execute(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    node = SchedulerNode(project, "stepone", "0")
    node.task.setup_work_directory(node.workdir)

    with patch("siliconcompiler.scheduler.SchedulerNode.execute") as call_exec:
        call_exec.side_effect = ValueError("thiserrorisraised")
        with pytest.raises(SystemExit):
            node.run()
        call_exec.assert_called_once()

    assert project.get("metric", "tasktime", step="stepone", index="0") is None
    assert project.get("metric", "totaltime", step="stepone", index="0") is None
    assert project.get("record", "status", step="stepone", index="0") == NodeStatus.ERROR

    assert "thiserrorisraised" in caplog.text
    assert "Halting stepone/0 due to errors" in caplog.text


def test_run_failed_to_execute_initial_save_has_error(project):
    node = SchedulerNode(project, "stepone", "0")
    node.task.setup_work_directory(node.workdir)

    assert node._SchedulerNode__generate_test_case is True

    with patch("siliconcompiler.Task.run_task") as run_task, \
            patch("siliconcompiler.scheduler.SchedulerNode.halt") as halt, \
            patch("siliconcompiler.scheduler.SchedulerNode._SchedulerNode__generate_testcase") as \
            testcase:
        run_task.return_value = 1

        def halt_step(*args, **kwargs):
            raise ValueError
        halt.side_effect = halt_step

        with pytest.raises(ValueError):
            node.run()

        run_task.assert_called_once()
        testcase.assert_called_once()

    assert project.get("record", "status", step="stepone", index="0") == NodeStatus.ERROR
    saved_manifest = Project.from_manifest(filepath=node.get_manifest())
    assert saved_manifest.get("record", "status", step="stepone", index="0") == NodeStatus.ERROR


def test_run_failed_to_execute_generate_issue(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    node = SchedulerNode(project, "stepone", "0")
    node.task.setup_work_directory(node.workdir)

    assert node._SchedulerNode__generate_test_case is True

    with patch("siliconcompiler.Task.run_task") as run_task, \
            patch("siliconcompiler.scheduler.SchedulerNode._SchedulerNode__generate_testcase") as \
            testcase:
        run_task.return_value = 1
        with pytest.raises(SystemExit):
            node.run()
        run_task.assert_called_once()
        testcase.assert_called_once()

    assert project.get("record", "status", step="stepone", index="0") == NodeStatus.ERROR
    saved_manifest = Project.from_manifest(filepath=node.get_manifest())
    assert saved_manifest.get("record", "status", step="stepone", index="0") == NodeStatus.ERROR

    assert "Halting stepone/0 due to errors" in caplog.text


def test_run_without_queue(project):
    node = SchedulerNode(project, "stepone", "0")
    node.task.setup_work_directory(node.workdir)
    with patch("logging.Logger.removeHandler") as call_remove_logger, \
         patch("siliconcompiler.scheduler.SchedulerNode.execute") as call_exec:
        node.run()
        call_exec.assert_called_once()
        call_remove_logger.assert_not_called()


def test_run_with_queue(project):
    node = SchedulerNode(project, "stepone", "0")

    class DummyPipe:
        calls = 0

        def send(self, *args, **kwargs):
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


def test_run_called_testcase_on_error(project):
    node = SchedulerNode(project, "stepone", "0")
    assert node._SchedulerNode__generate_test_case is True

    node.task.setup_work_directory(node.workdir)
    node._SchedulerNode__error = True

    with patch("siliconcompiler.scheduler.SchedulerNode."
               "_SchedulerNode__generate_testcase") as call_testcase:
        with pytest.raises(SystemExit):
            node.run()
        call_testcase.assert_called_once()


def test_run_not_called_testcase_on_error(project):
    node = SchedulerNode(project, "stepone", "0", replay=True)
    assert node._SchedulerNode__generate_test_case is False

    node.task.setup_work_directory(node.workdir)
    node._SchedulerNode__error = True

    with patch("siliconcompiler.scheduler.SchedulerNode."
               "_SchedulerNode__generate_testcase") as call_testcase:
        with pytest.raises(SystemExit):
            node.run()
        call_testcase.assert_not_called()


def test_copy_from_do_nothing(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    node = SchedulerNode(project, "stepone", "0")
    node.copy_from("test")
    assert caplog.text == ""


def test_copy_from(project, monkeypatch, caplog, has_graphviz):
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


def test_switch_node(project):
    node0 = SchedulerNode(project, "stepone", "0")
    node1 = node0.switch_node("steptwo", "2")
    assert node0.step == "stepone"
    assert node0.index == "0"
    assert node1.step == "steptwo"
    assert node1.index == "2"
    assert node0.project is node1.project


def test_scheduler_flow_reset_exception_exists():
    """Test that SchedulerFlowReset exception class exists and can be imported."""
    from siliconcompiler.scheduler.schedulernode import SchedulerFlowReset

    # Test that it's an Exception subclass
    assert issubclass(SchedulerFlowReset, Exception)

    # Test that it can be instantiated
    exc = SchedulerFlowReset("test message")
    assert str(exc) == "test message"


def test_scheduler_flow_reset_exception_can_be_raised():
    """Test that SchedulerFlowReset exception can be raised and caught."""
    from siliconcompiler.scheduler.schedulernode import SchedulerFlowReset

    msg = "Flow changed"
    with pytest.raises(SchedulerFlowReset) as exc_info:
        raise SchedulerFlowReset(msg)

    assert "Flow changed" in str(exc_info.value)


def test_check_previous_run_status_flow_raises_scheduler_flow_reset(project):
    """Test that check_previous_run_status raises SchedulerFlowReset when flow name changes."""
    node = SchedulerNode(project, "steptwo", "0")

    # Create a different flow with different name
    flow = Flowgraph("completely_different_flow")
    flow.node("stepone", NOPTask())
    flow.node("steptwo", NOPTask())
    flow.edge("stepone", "steptwo")

    other_project = Project(project.design)
    other_project.set_flow(flow)
    other_project.add_fileset("rtl")
    node_other = SchedulerNode(other_project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        with pytest.raises(SchedulerFlowReset) as exc_info:
            node.check_previous_run_status(node_other)

    assert "Flow name changed" in str(exc_info.value)
    assert "require full reset" in str(exc_info.value)


def test_check_previous_run_status_flow_different_name_vs_original(project):
    """Test check_previous_run_status with flow name that differs from original run."""
    # Set up first node with original flow
    node = SchedulerNode(project, "steptwo", "0")

    # Create second project with different flow name
    flow_new = Flowgraph("newflowname")
    flow_new.node("stepone", NOPTask())
    flow_new.node("steptwo", NOPTask())
    flow_new.edge("stepone", "steptwo")

    new_project = Project(project.design)
    new_project.set_flow(flow_new)
    new_project.add_fileset("rtl")
    node_new = SchedulerNode(new_project, "steptwo", "0")

    # Comparing nodes with different flow names should raise SchedulerFlowReset
    with node.runtime(), node_new.runtime():
        with pytest.raises(SchedulerFlowReset, match="^Flow name changed, require full reset$"):
            node.check_previous_run_status(node_new)


def test_check_previous_run_status_same_flow_name_passes(project, monkeypatch):
    """Test that check_previous_run_status passes when flow names match."""
    project.set("record", "status", NodeStatus.SUCCESS, step="steptwo", index="0")
    project.set("record", "inputnode", [("stepone", "0")], step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")

    def dummy_select(*_, **__):
        return [("stepone", "0")]
    monkeypatch.setattr(node.task, "select_input_nodes", dummy_select)

    # Same flow should not raise SchedulerFlowReset
    with node.runtime():
        node.check_previous_run_status(node)


def test_check_previous_run_status_flow_name_case_sensitive(project):
    """Test that flow name comparison is case-sensitive."""
    node = SchedulerNode(project, "steptwo", "0")

    # Create flow with different case
    flow_case = Flowgraph("TESTFLOW")  # Original is "testflow"
    flow_case.node("stepone", NOPTask())
    flow_case.node("steptwo", NOPTask())
    flow_case.edge("stepone", "steptwo")

    other_project = Project(project.design)
    other_project.set_flow(flow_case)
    other_project.add_fileset("rtl")
    node_other = SchedulerNode(other_project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        with pytest.raises(SchedulerFlowReset):
            node.check_previous_run_status(node_other)


def test_check_previous_run_status_flow_name_with_special_chars(project):
    """Test check_previous_run_status with flow names containing special characters."""
    node = SchedulerNode(project, "steptwo", "0")

    # Create flow with special characters in name
    flow_special = Flowgraph("test-flow_v20")
    flow_special.node("stepone", NOPTask())
    flow_special.node("steptwo", NOPTask())
    flow_special.edge("stepone", "steptwo")

    other_project = Project(project.design)
    other_project.set_flow(flow_special)
    other_project.add_fileset("rtl")
    node_other = SchedulerNode(other_project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        with pytest.raises(SchedulerFlowReset):
            node.check_previous_run_status(node_other)


def test_check_previous_run_status_preserves_other_error_paths(project):
    """Test that check_previous_run_status still returns False for non-flow errors."""
    # Set up node with RUNNING status (should still return False, not raise)
    project.set("record", "status", NodeStatus.RUNNING, step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")

    with node.runtime():
        with pytest.raises(SchedulerNodeResetSilent,
                           match=r"^Previous step did not complete$"):
            node.check_previous_run_status(node)


def test_check_previous_run_status_error_status_returns_false(project):
    """Test that check_previous_run_status returns False for ERROR status."""
    # Set up node with ERROR status
    project.set("record", "status", NodeStatus.ERROR, step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")

    with node.runtime():
        with pytest.raises(SchedulerNodeResetSilent,
                           match=r"^Previous step was not successful$"):
            node.check_previous_run_status(node)


def test_check_previous_run_status_tool_change_returns_false(project):
    """Test that check_previous_run_status returns False when tool changes."""
    node = SchedulerNode(project, "steptwo", "0")

    # Create flow with different task (different tool)
    flow = Flowgraph("testflow")  # Same flow name
    flow.node("stepone", NOPTask())
    flow.node("steptwo", EchoTask())  # Different task
    flow.edge("stepone", "steptwo")

    other_project = Project(project.design)
    other_project.set_flow(flow)
    other_project.add_fileset("rtl")
    node_other = SchedulerNode(other_project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        with pytest.raises(SchedulerNodeResetSilent,
                           match=r"^Tool name changed$"):
            node.check_previous_run_status(node_other)


def test_check_previous_run_status_combined_flow_and_tool_change(project):
    """Test behavior when both flow name and tool change."""
    node = SchedulerNode(project, "steptwo", "0")

    # Create flow with both different name AND different task
    flow_new = Flowgraph("differentflow")
    flow_new.node("stepone", NOPTask())
    flow_new.node("steptwo", EchoTask())
    flow_new.edge("stepone", "steptwo")

    other_project = Project(project.design)
    other_project.set_flow(flow_new)
    other_project.add_fileset("rtl")
    node_other = SchedulerNode(other_project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        # Flow name check happens first, so should raise SchedulerFlowReset
        # before checking tool
        with pytest.raises(SchedulerFlowReset):
            node.check_previous_run_status(node_other)


def test_check_previous_run_status_input_nodes_change_returns_false(project, monkeypatch):
    """Test that check_previous_run_status returns False when input nodes change."""
    project.set("record", "status", NodeStatus.SUCCESS, step="steptwo", index="0")
    project.set("record", "inputnode", [("stepone", "0")], step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")

    # Mock to return different input nodes
    def dummy_select(*_, **__):
        return [("stepone", "1")]  # Different index
    monkeypatch.setattr(node.task, "select_input_nodes", dummy_select)

    with node.runtime():
        with pytest.raises(SchedulerNodeReset,
                           match=r"^inputs to steptwo/0 has been modified from previous run$"):
            node.check_previous_run_status(node)


def test_scheduler_flow_reset_message_format():
    """Test that SchedulerFlowReset has a descriptive message."""
    from siliconcompiler.scheduler.schedulernode import SchedulerFlowReset

    # Test with custom message
    exc = SchedulerFlowReset("Custom reset message")
    assert str(exc) == "Custom reset message"

    # Test with default usage from code
    exc = SchedulerFlowReset("Flow name changed, require full reset")
    assert "Flow name changed" in str(exc)
    assert "require full reset" in str(exc)


def test_check_previous_run_status_unicode_flow_name(project):
    """Test check_previous_run_status with unicode characters in flow name."""
    node = SchedulerNode(project, "steptwo", "0")

    # Create flow with unicode in name
    flow_unicode = Flowgraph("test_流程_flow")
    flow_unicode.node("stepone", NOPTask())
    flow_unicode.node("steptwo", NOPTask())
    flow_unicode.edge("stepone", "steptwo")

    other_project = Project(project.design)
    other_project.set_flow(flow_unicode)
    other_project.add_fileset("rtl")
    node_other = SchedulerNode(other_project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        with pytest.raises(SchedulerFlowReset):
            node.check_previous_run_status(node_other)


def test_check_previous_run_status_whitespace_in_flow_name(project):
    """Test check_previous_run_status with whitespace differences in flow name."""
    node = SchedulerNode(project, "steptwo", "0")

    # Create flow with whitespace (should be different)
    flow_ws = Flowgraph(" testflow")  # Leading space
    flow_ws.node("stepone", NOPTask())
    flow_ws.node("steptwo", NOPTask())
    flow_ws.edge("stepone", "steptwo")

    other_project = Project(project.design)
    other_project.set_flow(flow_ws)
    other_project.add_fileset("rtl")
    node_other = SchedulerNode(other_project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        with pytest.raises(SchedulerFlowReset):
            node.check_previous_run_status(node_other)


def test_check_previous_run_status_long_flow_name(project):
    """Test check_previous_run_status with very long flow name."""
    node = SchedulerNode(project, "steptwo", "0")

    # Create flow with very long name
    long_name = "a" * 1000
    flow_long = Flowgraph(long_name)
    flow_long.node("stepone", NOPTask())
    flow_long.node("steptwo", NOPTask())
    flow_long.edge("stepone", "steptwo")

    other_project = Project(project.design)
    other_project.set_flow(flow_long)
    other_project.add_fileset("rtl")
    node_other = SchedulerNode(other_project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        with pytest.raises(SchedulerFlowReset):
            node.check_previous_run_status(node_other)


def test_check_previous_run_status_numeric_flow_name(project):
    """Test check_previous_run_status with numeric flow name."""
    node = SchedulerNode(project, "steptwo", "0")

    # Create flow with numeric name
    flow_num = Flowgraph("12345")
    flow_num.node("stepone", NOPTask())
    flow_num.node("steptwo", NOPTask())
    flow_num.edge("stepone", "steptwo")

    other_project = Project(project.design)
    other_project.set_flow(flow_num)
    other_project.add_fileset("rtl")
    node_other = SchedulerNode(other_project, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        with pytest.raises(SchedulerFlowReset):
            node.check_previous_run_status(node_other)


def test_check_previous_run_status_preserves_success_path(project, monkeypatch):
    """Test that successful reuse path still works correctly."""
    # Set up successful previous run
    project.set("record", "status", NodeStatus.SUCCESS, step="steptwo", index="0")
    project.set("record", "inputnode", [("stepone", "0")], step="steptwo", index="0")

    node = SchedulerNode(project, "steptwo", "0")

    # Mock to return same input nodes
    def dummy_select(*_, **__):
        return [("stepone", "0")]
    monkeypatch.setattr(node.task, "select_input_nodes", dummy_select)

    with node.runtime():
        # Should succeed without raising exception
        node.check_previous_run_status(node)


@pytest.mark.timeout(180)
def test_generate_testcase_autoissue(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    project.option.set_autoissue(True)
    assert project.option.get_autoissue() is True

    node = SchedulerNode(project, "stepone", "0")
    node.task.setup_work_directory(node.workdir)

    with patch("siliconcompiler.utils.issue.generate_testcase") as testcase:
        node._SchedulerNode__generate_testcase()
        testcase.assert_called_once()

    assert caplog.text == ""


@pytest.mark.timeout(180)
def test_generate_testcase_no_autoissue_no_manifest(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    assert project.option.get_autoissue() is False

    node = SchedulerNode(project, "stepone", "0")
    node.task.setup_work_directory(node.workdir)

    with patch("siliconcompiler.utils.issue.generate_testcase") as testcase:
        node._SchedulerNode__generate_testcase()
        testcase.assert_called_once()

    assert caplog.text == ""


@pytest.mark.timeout(180)
def test_generate_testcase_no_autoissue_output_manifest(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    assert project.option.get_autoissue() is False

    node = SchedulerNode(project, "stepone", "0")
    node.task.setup_work_directory(node.workdir)
    with open(node.get_manifest(input=False), "w"):
        pass

    with patch("siliconcompiler.utils.issue.generate_testcase") as testcase:
        node._SchedulerNode__generate_testcase()
        testcase.assert_not_called()

    assert "To generate a testcase, run: sc-issue -cfg " \
        f"{os.path.relpath('build/testdesign/job0/stepone/0/outputs/testdesign.pkg.json', '.')}" \
        in caplog.text


@pytest.mark.timeout(180)
def test_generate_testcase_no_autoissue_input_manifest(project, monkeypatch, caplog):
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)

    assert project.option.get_autoissue() is False

    node = SchedulerNode(project, "stepone", "0")
    node.task.setup_work_directory(node.workdir)
    with open(node.get_manifest(input=True), "w"):
        pass

    with patch("siliconcompiler.utils.issue.generate_testcase") as testcase:
        node._SchedulerNode__generate_testcase()
        testcase.assert_not_called()

    assert "To generate a testcase, run: sc-issue -cfg " \
        f"{os.path.relpath('build/testdesign/job0/stepone/0/inputs/testdesign.pkg.json', '.')}" \
        in caplog.text


def test_set_env(project, monkeypatch):
    project.set("tool", "builtin", "task", "nop", "env", "THIS", "TEST")
    monkeypatch.delenv("THIS", raising=False)
    assert "THIS" not in os.environ
    node = SchedulerNode(project, "stepone", "0")
    with node.runtime():
        with node._SchedulerNode__set_env():
            assert os.environ.get("THIS") == "TEST"
    assert "THIS" not in os.environ


def test_get_exe_path(project):
    with patch("siliconcompiler.Task.get_exe") as get_exe, \
            patch("siliconcompiler.scheduler.SchedulerNode._SchedulerNode__set_env") as set_env:
        get_exe.return_value = "this/path"
        node = SchedulerNode(project, "stepone", "0")
        with node.runtime():
            assert node.get_exe_path() == "this/path"
        get_exe.assert_called_once()
        set_env.assert_called_once()


def test_check_version_pass(project):
    project.option.set_novercheck(False, step="stepone", index="0")

    with patch("siliconcompiler.Task.get_exe_version") as get_exe_version, \
            patch("siliconcompiler.Task.check_exe_version") as check_exe_version, \
            patch("siliconcompiler.scheduler.SchedulerNode._SchedulerNode__set_env") as set_env:
        get_exe_version.return_value = "thisversion"
        check_exe_version.return_value = True
        node = SchedulerNode(project, "stepone", "0")
        with node.runtime():
            assert node.check_version() == ("thisversion", True)
        get_exe_version.assert_called_once()
        check_exe_version.assert_called_once_with("thisversion")
        set_env.assert_called_once()


def test_check_version_fail(project):
    project.option.set_novercheck(False, step="stepone", index="0")

    with patch("siliconcompiler.Task.get_exe_version") as get_exe_version, \
            patch("siliconcompiler.Task.check_exe_version") as check_exe_version, \
            patch("siliconcompiler.scheduler.SchedulerNode._SchedulerNode__set_env") as set_env:
        get_exe_version.return_value = "thisversion"
        check_exe_version.return_value = False
        node = SchedulerNode(project, "stepone", "0")
        with node.runtime():
            assert node.check_version() == ("thisversion", False)
        get_exe_version.assert_called_once()
        check_exe_version.assert_called_once_with("thisversion")
        set_env.assert_called_once()


def test_check_version_with_version(project):
    project.option.set_novercheck(False, step="stepone", index="0")

    with patch("siliconcompiler.Task.get_exe_version") as get_exe_version, \
            patch("siliconcompiler.Task.check_exe_version") as check_exe_version, \
            patch("siliconcompiler.scheduler.SchedulerNode._SchedulerNode__set_env") as set_env:
        check_exe_version.return_value = False
        node = SchedulerNode(project, "stepone", "0")
        with node.runtime():
            assert node.check_version("thisversion") == ("thisversion", False)
        get_exe_version.assert_not_called()
        check_exe_version.assert_called_once_with("thisversion")
        set_env.assert_called_once()


def test_check_version_nocheck(project):
    project.option.set_novercheck(True, step="stepone", index="0")

    with patch("siliconcompiler.Task.get_exe_version") as get_exe_version, \
            patch("siliconcompiler.Task.check_exe_version") as check_exe_version, \
            patch("siliconcompiler.scheduler.SchedulerNode._SchedulerNode__set_env") as set_env:
        get_exe_version.return_value = "thisversion"
        check_exe_version.return_value = False
        node = SchedulerNode(project, "stepone", "0")
        with node.runtime():
            assert node.check_version() == (None, True)
        get_exe_version.assert_not_called()
        check_exe_version.assert_not_called()
        set_env.assert_not_called()


@pytest.mark.parametrize("reset", (SchedulerNodeReset, SchedulerNodeResetSilent))
def test_scheduler_reset_except_msg(reset):
    assert reset("this msg").msg == "this msg"


def test_scheduler_reset_except():
    assert SchedulerNodeReset("").silent() is False


def test_scheduler_reset_silent_except():
    assert SchedulerNodeResetSilent("").silent() is True
