import copy
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

from siliconcompiler import Chip, Flow, Schema
from siliconcompiler import NodeStatus
from siliconcompiler import TaskSchema
from siliconcompiler.tools.builtin import nop, join
from scheduler.tools.echo import echo

from siliconcompiler.scheduler.schedulernode import SchedulerNode


@pytest.fixture
def chip():
    flow = Flow("testflow")

    flow.node("testflow", "stepone", nop)
    flow.node("testflow", "steptwo", nop)
    flow.edge("testflow", "stepone", "steptwo")

    chip = Chip("dummy")
    chip.use(flow)
    chip.set("option", "flow", "testflow")
    chip.set("tool", "builtin", "task", "nop", "threads", 1)

    return chip


@pytest.fixture
def echo_chip():
    flow = Flow("testflow")

    flow.node("testflow", "stepone", echo)
    flow.node("testflow", "steptwo", echo)
    flow.edge("testflow", "stepone", "steptwo")

    chip = Chip("dummy")
    chip.use(flow)
    chip.set("option", "flow", "testflow")
    chip.set("tool", "echo", "task", "echo", "threads", 1)

    return chip


def test_init(chip):
    node = SchedulerNode(chip, "stepone", "0")

    assert node.is_local is True
    assert node.is_builtin is False
    assert node.has_error is False
    assert node.step == "stepone"
    assert node.index == "0"
    assert node.name == "dummy"
    assert node.topmodule == "dummy"
    assert node.chip is chip
    assert node.logger is chip.logger
    assert node.jobname == "job0"
    assert node.is_replay is False
    assert isinstance(node.task, TaskSchema)
    assert node.jobworkdir == chip.getworkdir()
    assert node.workdir == os.path.join(node.jobworkdir, "stepone", "0")

    # Check private fields
    assert node._SchedulerNode__record_user_info is False
    assert node._SchedulerNode__generate_test_case is True
    assert node._SchedulerNode__hash is False
    assert node._SchedulerNode__is_entry_node is True


def test_init_different_top(chip):
    chip.set("option", "entrypoint", "thistop", step="stepone")
    node = SchedulerNode(chip, "stepone", "0")

    assert node.is_local is True
    assert node.is_builtin is False
    assert node.has_error is False
    assert node.step == "stepone"
    assert node.index == "0"
    assert node.name == "dummy"
    assert node.topmodule == "thistop"
    assert node.chip is chip
    assert node.logger is chip.logger
    assert node.jobname == "job0"
    assert node.is_replay is False
    assert isinstance(node.task, TaskSchema)
    assert node.jobworkdir == chip.getworkdir()
    assert node.workdir == os.path.join(node.jobworkdir, "stepone", "0")

    # Check private fields
    assert node._SchedulerNode__record_user_info is False
    assert node._SchedulerNode__generate_test_case is True
    assert node._SchedulerNode__hash is False
    assert node._SchedulerNode__is_entry_node is True


def test_init_replay(chip):
    node = SchedulerNode(chip, "stepone", "0", replay=True)

    assert node.is_local is True
    assert node.is_builtin is False
    assert node.has_error is False
    assert node.step == "stepone"
    assert node.index == "0"
    assert node.name == "dummy"
    assert node.topmodule == "dummy"
    assert node.chip is chip
    assert node.logger is chip.logger
    assert node.jobname == "job0"
    assert node.is_replay is True
    assert isinstance(node.task, TaskSchema)
    assert node.jobworkdir == chip.getworkdir()
    assert node.workdir == os.path.join(node.jobworkdir, "stepone", "0")

    # Check private fields
    assert node._SchedulerNode__record_user_info is False
    assert node._SchedulerNode__generate_test_case is False
    assert node._SchedulerNode__hash is False
    assert node._SchedulerNode__is_entry_node is True


def test_init_not_entry(chip):
    node = SchedulerNode(chip, "steptwo", "0")

    assert node.is_local is True
    assert node.is_builtin is False
    assert node.has_error is False
    assert node.step == "steptwo"
    assert node.index == "0"
    assert node.name == "dummy"
    assert node.topmodule == "dummy"
    assert node.chip is chip
    assert node.logger is chip.logger
    assert node.jobname == "job0"
    assert node.is_replay is False
    assert isinstance(node.task, TaskSchema)
    assert node.jobworkdir == chip.getworkdir()
    assert node.workdir == os.path.join(node.jobworkdir, "steptwo", "0")

    # Check private fields
    assert node._SchedulerNode__record_user_info is False
    assert node._SchedulerNode__generate_test_case is True
    assert node._SchedulerNode__hash is False
    assert node._SchedulerNode__is_entry_node is False


def test_set_builtin(chip):
    node = SchedulerNode(chip, "steptwo", "0")
    assert node.is_builtin is False
    node.set_builtin()
    assert node.is_builtin is True


@pytest.mark.nostrict
def test_threads(chip):
    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        assert node.threads == 1
    assert chip.schema.set("tool", "builtin", "task", "nop", "threads", 10)
    with node.runtime():
        assert node.threads == 10


def test_get_manifest_output(chip):
    node = SchedulerNode(chip, "steptwo", "0")
    assert node.get_manifest() == os.path.join(
        node.workdir, "outputs", f"{node.name}.pkg.json")


def test_get_manifest_input(chip):
    node = SchedulerNode(chip, "steptwo", "0")
    assert node.get_manifest(input=True) == os.path.join(
        node.workdir, "inputs", f"{node.name}.pkg.json")


@pytest.mark.parametrize(
    "type,expect_name", [
        ("exe", "steptwo.log"),
        ("sc", "sc_steptwo_0.log"),
    ])
def test_get_log(chip, type, expect_name):
    node = SchedulerNode(chip, "steptwo", "0")
    assert node.get_log(type) == os.path.join(
        node.workdir, expect_name)


def test_get_log_invalid(chip):
    node = SchedulerNode(chip, "steptwo", "0")
    with pytest.raises(ValueError, match="invalid is not a log"):
        node.get_log("invalid")


def test_halt(chip):
    node = SchedulerNode(chip, "steptwo", "0")
    node.task.setup_work_directory(node.workdir)

    with pytest.raises(SystemExit):
        node.halt()
    assert chip.get("record", "status", step="steptwo", index="0") == NodeStatus.ERROR
    assert os.path.exists("build/dummy/job0/steptwo/0/outputs/dummy.pkg.json")


def test_halt_with_reason(chip, caplog):
    chip.logger = logging.getLogger()
    node = SchedulerNode(chip, "steptwo", "0")
    node.task.setup_work_directory(node.workdir)

    with pytest.raises(SystemExit):
        node.halt("failed due to error")
    assert chip.get("record", "status", step="steptwo", index="0") == NodeStatus.ERROR
    assert os.path.exists("build/dummy/job0/steptwo/0/outputs/dummy.pkg.json")
    assert "failed due to error" in caplog.text


def test_setup(chip):
    node = SchedulerNode(chip, "steptwo", "0")

    with node.runtime():
        assert node.setup() is True


def test_setup_error(chip, monkeypatch, caplog):
    chip.logger = logging.getLogger()
    node = SchedulerNode(chip, "steptwo", "0")

    def dummy_setup(*args, **kwargs):
        raise ValueError("Find this")
    monkeypatch.setattr(node.task, "setup", dummy_setup)

    with node.runtime():
        with pytest.raises(ValueError, match="Find this"):
            node.setup()
    assert "Failed to run setup() for steptwo/0 with builtin/nop" in caplog.text


def test_setup_skipped(chip, monkeypatch, caplog):
    chip.logger = logging.getLogger()
    node = SchedulerNode(chip, "steptwo", "0")

    def dummy_setup(*args, **kwargs):
        return "skip me"
    monkeypatch.setattr(node.task, "setup", dummy_setup)

    with node.runtime():
        assert node.setup() is False
    assert chip.get("record", "status", step="steptwo", index="0") == NodeStatus.SKIPPED
    assert "Removing steptwo/0 due to skip me" in caplog.text


def test_clean_directory(chip):
    node = SchedulerNode(chip, "steptwo", "0")
    os.makedirs(node.workdir, exist_ok=True)
    assert os.path.exists(node.workdir)
    node.clean_directory()
    assert not os.path.exists(node.workdir)


def test_clean_directory_no_dir(chip):
    node = SchedulerNode(chip, "steptwo", "0")
    assert not os.path.exists(node.workdir)
    node.clean_directory()
    assert not os.path.exists(node.workdir)


def test_get_check_changed_keys(chip):
    node = SchedulerNode(chip, "steptwo", "0")
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


def test_get_check_changed_keys_with_invalid_require(chip):
    chip.add("tool", "builtin", "task", "nop", "require", "this,key")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        with pytest.raises(KeyError, match="\\[this,key\\] not found"):
            node.get_check_changed_keys()


def test_get_check_changed_keys_with_require(chip):
    chip.add("tool", "builtin", "task", "nop", "require", "option,idir")
    chip.add("tool", "builtin", "task", "nop", "require", "option,param,N")
    chip.set("tool", "builtin", "task", "nop", "env", "BUILD", "this")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        values, paths = node.get_check_changed_keys()
    assert values == {
        ('option', 'param', 'N'),
        ('tool', 'builtin', 'task', 'nop', 'env', "BUILD"),
        ('tool', 'builtin', 'task', 'nop', 'threads'),
        ('tool', 'builtin', 'task', 'nop', 'option')
    }
    assert paths == {
        ('option', 'idir'),
        ('tool', 'builtin', 'task', 'nop', 'refdir'),
        ('tool', 'builtin', 'task', 'nop', 'postscript'),
        ('tool', 'builtin', 'task', 'nop', 'prescript'),
        ('tool', 'builtin', 'task', 'nop', 'script')
    }


def test_check_values_changed_no_change(chip):
    chip.set("option", "param", "N", "64")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        assert node.check_values_changed(node, [("option", "param", "N")]) is False


def test_check_values_changed_change(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    chip.set("option", "param", "N", "64")

    node = SchedulerNode(chip, "steptwo", "0")

    other_chip = copy.deepcopy(chip)
    other_chip.set("option", "param", "N", "128")
    other = SchedulerNode(other_chip, "steptwo", "0")

    with node.runtime(), other.runtime():
        assert node.check_values_changed(other, [("option", "param", "N")]) is True
    assert "[option,param,N] in steptwo/0 has been modified from previous run" in caplog.text


def test_check_values_changed_change_missing(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        assert node.check_values_changed(node, [("option", "params", "N")]) is True
    assert "[option,params,N] in steptwo/0 has been modified from previous run" in caplog.text


def test_check_previous_run_status_flow(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)

    node = SchedulerNode(chip, "steptwo", "0")
    flow = Flow("testflow0")
    flow.node("testflow0", "stepone", nop)
    flow.node("testflow0", "steptwo", nop)
    flow.edge("testflow0", "stepone", "steptwo")
    chip = Chip("dummy")
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)
    chip.use(flow)
    chip.set("option", "flow", "testflow0")
    node_other = SchedulerNode(chip, "steptwo", "0")
    with node.runtime(), node_other.runtime():
        assert node.check_previous_run_status(node_other) is False
    assert "Flow name changed" in caplog.text


def test_check_previous_run_status_tool(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)

    node = SchedulerNode(chip, "steptwo", "0")
    flow = Flow("testflow")
    flow.node("testflow", "stepone", nop)
    flow.node("testflow", "steptwo", echo)
    flow.edge("testflow", "stepone", "steptwo")
    chip = Chip("dummy")
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)
    chip.use(flow)
    chip.set("option", "flow", "testflow")
    node_other = SchedulerNode(chip, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        assert node.check_previous_run_status(node_other) is False
    assert "Tool name changed" in caplog.text


def test_check_previous_run_status_task(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)

    node = SchedulerNode(chip, "steptwo", "0")
    flow = Flow("testflow")
    flow.node("testflow", "stepone", nop)
    flow.node("testflow", "steptwo", join)
    flow.edge("testflow", "stepone", "steptwo")
    chip = Chip("dummy")
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)
    chip.use(flow)
    chip.set("option", "flow", "testflow")
    node_other = SchedulerNode(chip, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        assert node.check_previous_run_status(node_other) is False
    assert "Task name changed" in caplog.text


def test_check_previous_run_status_running(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)

    chip.set("record", "status", NodeStatus.RUNNING, step="steptwo", index="0")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        assert node.check_previous_run_status(node) is False
    assert "Previous step did not complete" in caplog.text


def test_check_previous_run_status_failed(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)

    chip.set("record", "status", NodeStatus.ERROR, step="steptwo", index="0")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        assert node.check_previous_run_status(node) is False
    assert "Previous step was not successful" in caplog.text


def test_check_previous_run_status_inputs_changed(chip, monkeypatch, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    chip.set("record", "status", NodeStatus.SUCCESS, step="steptwo", index="0")
    chip.set("record", "inputnode", [("stepone", "0")], step="steptwo", index="0")

    def dummy_select(*args, **kwargs):
        return [("test", "1")]

    node = SchedulerNode(chip, "steptwo", "0")
    monkeypatch.setattr(node.task, "select_input_nodes", dummy_select)

    with node.runtime():
        assert node.check_previous_run_status(node) is False
    assert "inputs to steptwo/0 has been modified from previous run" in caplog.text


def test_check_previous_run_status_no_change(chip, monkeypatch):
    node = SchedulerNode(chip, "steptwo", "0")
    chip.set("record", "status", NodeStatus.SUCCESS, step="steptwo", index="0")
    chip.set("record", "inputnode", [("stepone", "0")], step="steptwo", index="0")

    def dummy_select(*args, **kwargs):
        return [("stepone", "0")]
    monkeypatch.setattr(node.task, "select_input_nodes", dummy_select)

    with node.runtime():
        assert node.check_previous_run_status(node) is True


def test_check_files_changed_timestamp_no_change(chip):
    with open("testfile.txt", "w") as f:
        f.write("test")

    now = time.time() + 1
    chip.set("option", "file", "test", "testfile.txt")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        assert node.check_files_changed(node, now, [("option", "file", "test")]) is False


def test_check_files_changed_timestamp(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    now = time.time() - 1

    with open("testfile.txt", "w") as f:
        f.write("test")

    chip.set("option", "file", "test", "testfile.txt")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        assert node.check_files_changed(node, now, [("option", "file", "test")]) is True
    assert "[option,file,test] (timestamp) in steptwo/0 has been modified from previous run" in \
        caplog.text


def test_check_files_changed_directory(chip):
    os.makedirs("testdir", exist_ok=True)

    with open("testdir/testfile.txt", "w") as f:
        f.write("test")

    now = time.time() + 1

    chip.set("option", "dir", "test", "testdir")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        assert node.check_files_changed(node, now, [("option", "dir", "test")]) is False


def test_check_files_changed_timestamp_directory(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    now = time.time() - 1

    os.makedirs("testdir", exist_ok=True)

    with open("testdir/testfile.txt", "w") as f:
        f.write("test")

    chip.set("option", "dir", "test", "testdir")
    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        assert node.check_files_changed(node, now, [("option", "dir", "test")]) is True
    assert "[option,dir,test] (timestamp) in steptwo/0 has been modified from previous run" in \
        caplog.text


def test_check_files_changed_package(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    now = time.time() - 1

    with open("testfile.txt", "w") as f:
        f.write("test")

    node = SchedulerNode(chip, "steptwo", "0")
    chip.set("option", "file", "test", "testfile.txt")

    node_other = SchedulerNode(copy.deepcopy(chip), "steptwo", "0")

    chip.set("option", "file", "test", "testfile.txt", package="testing")

    with node.runtime(), node_other.runtime():
        assert node.check_files_changed(node_other, now, [("option", "file", "test")]) is True
    assert "[option,file,test] (file package) in steptwo/0 has been modified from previous run" in \
        caplog.text


def test_check_files_changed_timestamp_current_hash(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    now = time.time() - 1

    with open("testfile.txt", "w") as f:
        f.write("test")

    chip.set("option", "file", "test", "testfile.txt")

    node_other = SchedulerNode(copy.deepcopy(chip), "steptwo", "0")

    chip.set("option", "hash", True)
    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime(), node_other.runtime():
        assert node.check_files_changed(node_other, now, [("option", "file", "test")]) is True
    assert "[option,file,test] (timestamp) in steptwo/0 has been modified from previous run" in \
        caplog.text


def test_check_files_changed_timestamp_previous_hash(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    now = time.time() - 1

    with open("testfile.txt", "w") as f:
        f.write("test")

    chip.set("option", "file", "test", "testfile.txt")

    node = SchedulerNode(chip, "steptwo", "0")
    chip = copy.deepcopy(chip)
    chip.set("option", "hash", True)
    node_other = SchedulerNode(chip, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        assert node.check_files_changed(node_other, now, [("option", "file", "test")]) is True
    assert "[option,file,test] (timestamp) in steptwo/0 has been modified from previous run" in \
        caplog.text


def test_check_files_changed_hash_no_change(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    now = time.time() - 1

    with open("testfile.txt", "w") as f:
        f.write("test")

    chip.set("option", "hash", True)
    chip.set("option", "file", "test", "testfile.txt")
    other_chip = copy.deepcopy(chip)

    chip.hash_files("option", "dir", "test")

    node = SchedulerNode(chip, "steptwo", "0")
    node_other = SchedulerNode(other_chip, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        assert node.check_files_changed(node_other, now, [("option", "dir", "test")]) is False


def test_check_files_changed_hash_directory(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    now = time.time() - 1

    os.makedirs("testdir", exist_ok=True)

    with open("testdir/testfile.txt", "w") as f:
        f.write("test")

    chip.set("option", "hash", True)
    chip.set("option", "dir", "test", "testdir")
    other_chip = copy.deepcopy(chip)

    chip.hash_files("option", "dir", "test")

    with open("testdir/testfile.txt", "w") as f:
        f.write("testing")

    node = SchedulerNode(chip, "steptwo", "0")
    node_other = SchedulerNode(other_chip, "steptwo", "0")

    with node.runtime(), node_other.runtime():
        assert node.check_files_changed(node_other, now, [("option", "dir", "test")]) is True
    assert "[option,dir,test] (file hash) in steptwo/0 has been modified from previous run" in \
        caplog.text


def test_requires_run_fail_input(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)

    node = SchedulerNode(chip, "steptwo", "0")

    assert node.requires_run() is True
    assert "Previous run did not generate input manifest" in \
        caplog.text


def test_requires_run_fail_output(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)

    node = SchedulerNode(chip, "steptwo", "0")

    os.makedirs(os.path.dirname(node.get_manifest(input=True)))
    chip.write_manifest(node.get_manifest(input=True))

    assert node.requires_run() is True
    assert "Previous run did not generate output manifest" in \
        caplog.text


def test_requires_run_all_pass(chip, monkeypatch):
    node = SchedulerNode(chip, "steptwo", "0")

    os.makedirs(os.path.dirname(node.get_manifest(input=True)))
    chip.write_manifest(node.get_manifest(input=True))
    os.makedirs(os.path.dirname(node.get_manifest()))
    chip.write_manifest(node.get_manifest())

    def dummy_get_check_changed_keys(*args):
        return (set(), set())
    monkeypatch.setattr(node, "get_check_changed_keys", dummy_get_check_changed_keys)

    def dummy_check_previous_run_status(*args):
        return True
    monkeypatch.setattr(node, "check_previous_run_status", dummy_check_previous_run_status)

    assert node.requires_run() is False


def test_requires_run_all_input_corrupt(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)

    node = SchedulerNode(chip, "steptwo", "0")

    os.makedirs(os.path.dirname(node.get_manifest(input=True)))
    with open(node.get_manifest(input=True), "w") as f:
        f.write("this is not a json file")

    assert node.requires_run() is True
    assert "Input manifest failed to load" in caplog.text


def test_requires_run_all_output_corrupt(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)

    node = SchedulerNode(chip, "steptwo", "0")

    os.makedirs(os.path.dirname(node.get_manifest(input=True)))
    chip.write_manifest(node.get_manifest(input=True))

    os.makedirs(os.path.dirname(node.get_manifest()))
    with open(node.get_manifest(), "w") as f:
        f.write("this is not a json file")

    assert node.requires_run() is True
    assert "Output manifest failed to load" in caplog.text


def test_requires_run_all_state_failed(chip, monkeypatch, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)

    node = SchedulerNode(chip, "steptwo", "0")

    os.makedirs(os.path.dirname(node.get_manifest(input=True)))
    chip.write_manifest(node.get_manifest(input=True))
    os.makedirs(os.path.dirname(node.get_manifest()))
    chip.write_manifest(node.get_manifest())

    def dummy_check_previous_run_status(*args):
        return False
    monkeypatch.setattr(node, "check_previous_run_status", dummy_check_previous_run_status)

    assert node.requires_run() is True
    assert "Previous run state failed" in caplog.text


def test_requires_run_all_keys_failed(chip, monkeypatch, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)

    node = SchedulerNode(chip, "steptwo", "0")

    os.makedirs(os.path.dirname(node.get_manifest(input=True)))
    chip.write_manifest(node.get_manifest(input=True))
    os.makedirs(os.path.dirname(node.get_manifest()))
    chip.write_manifest(node.get_manifest())

    def dummy_check_previous_run_status(*args):
        return True
    monkeypatch.setattr(node, "check_previous_run_status", dummy_check_previous_run_status)

    def dummy_get_check_changed_keys(*args):
        raise KeyError
    monkeypatch.setattr(node, "get_check_changed_keys", dummy_get_check_changed_keys)

    assert node.requires_run() is True
    assert "Failed to acquire keys" in caplog.text


def test_requires_run_all_values_changed(chip, monkeypatch, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)

    node = SchedulerNode(chip, "steptwo", "0")

    os.makedirs(os.path.dirname(node.get_manifest(input=True)))
    chip.write_manifest(node.get_manifest(input=True))
    os.makedirs(os.path.dirname(node.get_manifest()))
    chip.write_manifest(node.get_manifest())

    def dummy_check_previous_run_status(*args):
        return True
    monkeypatch.setattr(node, "check_previous_run_status", dummy_check_previous_run_status)

    def dummy_get_check_changed_keys(*args):
        return set(), set()
    monkeypatch.setattr(node, "get_check_changed_keys", dummy_get_check_changed_keys)

    def dummy_check_values_changed(*args):
        return True
    monkeypatch.setattr(node, "check_values_changed", dummy_check_values_changed)

    assert node.requires_run() is True
    assert "Key values changed" in caplog.text


def test_requires_run_all_files_changed(chip, monkeypatch, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.DEBUG)

    node = SchedulerNode(chip, "steptwo", "0")

    os.makedirs(os.path.dirname(node.get_manifest(input=True)))
    chip.write_manifest(node.get_manifest(input=True))
    os.makedirs(os.path.dirname(node.get_manifest()))
    chip.write_manifest(node.get_manifest())

    def dummy_check_previous_run_status(*args):
        return True
    monkeypatch.setattr(node, "check_previous_run_status", dummy_check_previous_run_status)

    def dummy_get_check_changed_keys(*args):
        return set(), set()
    monkeypatch.setattr(node, "get_check_changed_keys", dummy_get_check_changed_keys)

    def dummy_check_values_changed(*args):
        return False
    monkeypatch.setattr(node, "check_values_changed", dummy_check_values_changed)

    def dummy_check_files_changed(*args):
        return True
    monkeypatch.setattr(node, "check_files_changed", dummy_check_files_changed)

    assert node.requires_run() is True
    assert "Files changed" in caplog.text


@pytest.mark.nostrict
def test_check_logfile(chip, datadir, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    # add regex
    chip.add('tool', 'builtin', 'task', 'nop', 'regex', 'errors', "ERROR")
    chip.add('tool', 'builtin', 'task', 'nop', 'regex', 'warnings', "WARNING")
    chip.add('tool', 'builtin', 'task', 'nop', 'regex', 'warnings', "-v DPL")

    node = SchedulerNode(chip, "stepone", "0")
    assert chip.get("metric", "errors", step="stepone", index="0") is None
    assert chip.get("metric", "warnings", step="stepone", index="0") is None

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

    assert chip.get("metric", "errors", step="stepone", index="0") == 1
    assert chip.get("metric", "warnings", step="stepone", index="0") == 1


@pytest.mark.nostrict
def test_check_logfile_with_extra_metrics(chip, datadir, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    # add regex
    chip.add('tool', 'builtin', 'task', 'nop', 'regex', 'errors', "ERROR")
    chip.add('tool', 'builtin', 'task', 'nop', 'regex', 'warnings', "WARNING")
    chip.add('tool', 'builtin', 'task', 'nop', 'regex', 'warnings', "-v DPL")

    node = SchedulerNode(chip, "stepone", "0")
    assert chip.get("metric", "errors", step="stepone", index="0") is None
    assert chip.get("metric", "warnings", step="stepone", index="0") is None
    chip.set("metric", "errors", 5, step="stepone", index="0")
    chip.set("metric", "warnings", 11, step="stepone", index="0")

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

    assert chip.get("metric", "errors", step="stepone", index="0") == 6
    assert chip.get("metric", "warnings", step="stepone", index="0") == 12


@pytest.mark.nostrict
def test_check_logfile_none(chip, datadir, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    node = SchedulerNode(chip, "stepone", "0")
    assert chip.get("metric", "errors", step="stepone", index="0") is None
    assert chip.get("metric", "warnings", step="stepone", index="0") is None

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

    assert chip.get("metric", "errors", step="stepone", index="0") is None
    assert chip.get("metric", "warnings", step="stepone", index="0") is None


@pytest.mark.nostrict
def test_check_logfile_non_metric(chip, datadir, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    # add regex
    chip.add('tool', 'builtin', 'task', 'nop', 'regex', 'somethingelse', "ERROR")

    node = SchedulerNode(chip, "stepone", "0")
    assert chip.get("metric", "errors", step="stepone", index="0") is None
    assert chip.get("metric", "warnings", step="stepone", index="0") is None

    with node.runtime():
        # check log
        os.makedirs(node.workdir, exist_ok=True)
        shutil.copy(os.path.join(datadir, 'schedulernode', 'check_logfile.log'),
                    node.get_log())
        node.check_logfile()

    assert os.path.isfile("stepone.somethingelse")

    assert chip.get("metric", "errors", step="stepone", index="0") is None
    assert chip.get("metric", "warnings", step="stepone", index="0") is None


def test_setup_input_directory_do_nothing(chip):
    node = SchedulerNode(chip, "stepone", "0")
    with node.runtime():
        node.setup_input_directory()


def test_setup_input_directory(chip):
    output_dir = Path(chip.getworkdir(step="stepone", index="0")) / "outputs"
    input_dir = Path(chip.getworkdir(step="steptwo", index="0")) / "inputs"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(input_dir, exist_ok=True)

    jsonfile = output_dir / "dummy.pkg.json"
    jsonfile.touch()
    file0 = output_dir / "file0.txt"
    file0.touch()
    file1 = output_dir / "file1.txt"
    file1.touch()

    chip.set("record", "inputnode", ("stepone", "0"), step="steptwo", index="0")
    chip.set("tool", "builtin", "task", "nop", "input", "file0.txt", step="steptwo", index="0")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        node.setup_input_directory()

    assert os.path.isfile(input_dir / "file0.txt")
    assert not os.path.isfile(input_dir / "file1.txt")
    assert not os.path.isfile(input_dir / "dummy.pkg.json")


def test_setup_input_directory_not_strict(chip):
    output_dir = Path(chip.getworkdir(step="stepone", index="0")) / "outputs"
    input_dir = Path(chip.getworkdir(step="steptwo", index="0")) / "inputs"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(input_dir, exist_ok=True)

    jsonfile = output_dir / "dummy.pkg.json"
    jsonfile.touch()
    file0 = output_dir / "file0.txt"
    file0.touch()
    file1 = output_dir / "file1.txt"
    file1.touch()

    chip.set("option", "strict", False)
    chip.set("record", "inputnode", ("stepone", "0"), step="steptwo", index="0")
    chip.set("tool", "builtin", "task", "nop", "input", "file0.txt", step="steptwo", index="0")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        node.setup_input_directory()

    assert os.path.isfile(input_dir / "file0.txt")
    assert os.path.isfile(input_dir / "file1.txt")
    assert not os.path.isfile(input_dir / "dummy.pkg.json")


def test_setup_input_directory_directory(chip):
    output_dir = Path(chip.getworkdir(step="stepone", index="0")) / "outputs"
    input_dir = Path(chip.getworkdir(step="steptwo", index="0")) / "inputs"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(input_dir, exist_ok=True)

    jsonfile = output_dir / "dummy.pkg.json"
    jsonfile.touch()
    dir0 = output_dir / "dir0"
    dir0.mkdir(exist_ok=True)

    chip.set("record", "inputnode", ("stepone", "0"), step="steptwo", index="0")
    chip.set("tool", "builtin", "task", "nop", "input", "dir0", step="steptwo", index="0")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        node.setup_input_directory()

    assert os.path.isdir(input_dir / "dir0")
    assert not os.path.isfile(input_dir / "dummy.pkg.json")


def test_setup_input_directory_renames_dir(chip):
    output_dir = Path(chip.getworkdir(step="stepone", index="0")) / "outputs"
    input_dir = Path(chip.getworkdir(step="steptwo", index="0")) / "inputs"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(input_dir, exist_ok=True)

    jsonfile = output_dir / "dummy.pkg.json"
    jsonfile.touch()
    dir0 = output_dir / "dir0"
    dir0.mkdir(exist_ok=True)

    chip.set("record", "inputnode", ("stepone", "0"), step="steptwo", index="0")
    chip.set("tool", "builtin", "task", "nop", "input", "dir0.stepone0", step="steptwo", index="0")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        node.setup_input_directory()

    assert not os.path.exists(input_dir / "dir0")
    assert os.path.isdir(input_dir / "dir0.stepone0")
    assert not os.path.isfile(input_dir / "dummy.pkg.json")


def test_setup_input_directory_renames_file(chip):
    output_dir = Path(chip.getworkdir(step="stepone", index="0")) / "outputs"
    input_dir = Path(chip.getworkdir(step="steptwo", index="0")) / "inputs"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(input_dir, exist_ok=True)

    jsonfile = output_dir / "dummy.pkg.json"
    jsonfile.touch()
    file0 = output_dir / "file0.txt"
    file0.touch()
    file1 = output_dir / "file1.txt"
    file1.touch()

    chip.set("record", "inputnode", ("stepone", "0"), step="steptwo", index="0")
    chip.set("tool", "builtin", "task", "nop", "input", "file0.stepone0.txt",
             step="steptwo", index="0")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        node.setup_input_directory()

    assert not os.path.exists(input_dir / "file0.txt")
    assert os.path.isfile(input_dir / "file0.stepone0.txt")
    assert not os.path.isfile(input_dir / "dummy.pkg.json")


def test_setup_input_directory_no_input_dir(chip, caplog):
    chip.logger = logging.getLogger()

    input_dir = Path(chip.getworkdir(step="steptwo", index="0")) / "inputs"
    os.makedirs(input_dir, exist_ok=True)
    output_dir = Path(chip.getworkdir(step="steptwo", index="0")) / "outputs"
    os.makedirs(output_dir, exist_ok=True)

    chip.set("record", "inputnode", ("stepone", "0"), step="steptwo", index="0")
    chip.set("tool", "builtin", "task", "nop", "input", "file0.txt",
             step="steptwo", index="0")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        with pytest.raises(SystemExit):
            node.setup_input_directory()

    assert "Unable to locate outputs directory for stepone/0: " in caplog.text


@pytest.mark.parametrize("error", [NodeStatus.ERROR, NodeStatus.TIMEOUT])
def test_setup_input_directory_input_error(chip, error, caplog):
    chip.logger = logging.getLogger()

    input_dir = Path(chip.getworkdir(step="steptwo", index="0")) / "inputs"
    os.makedirs(input_dir, exist_ok=True)
    output_dir = Path(chip.getworkdir(step="steptwo", index="0")) / "outputs"
    os.makedirs(output_dir, exist_ok=True)

    chip.set("record", "status", error, step="stepone", index="0")
    chip.set("record", "inputnode", ("stepone", "0"), step="steptwo", index="0")
    chip.set("tool", "builtin", "task", "nop", "input", "file0.txt",
             step="steptwo", index="0")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        with pytest.raises(SystemExit):
            node.setup_input_directory()

    assert "Halting steptwo/0 due to errors" in caplog.text


def test_validate(chip):
    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        assert node.validate() is True


def test_validate_missing_inputs(chip, caplog):
    chip.logger = logging.getLogger()

    chip.set("tool", "builtin", "task", "nop", "input", "file0.txt",
             step="steptwo", index="0")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        assert node.validate() is False
    assert "Required input file0.txt not received for steptwo/0" in caplog.text


def test_validate_missing_required_key(chip, caplog):
    chip.logger = logging.getLogger()

    chip.set("tool", "builtin", "task", "nop", "require", ["key,not,found"],
             step="steptwo", index="0")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        assert node.validate() is False
    assert "Cannot resolve required keypath [key,not,found]" in caplog.text


def test_validate_empty_required_key(chip, caplog):
    chip.logger = logging.getLogger()

    chip.set("tool", "builtin", "task", "nop", "require", ["option,var,test"],
             step="steptwo", index="0")
    chip.set("option", "var", "test", "")
    chip.unset("option", "var", "test")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        assert node.validate() is False
    assert "No value set for required keypath [option,var,test]" in caplog.text


def test_validate_missing_required_file(chip, caplog):
    chip.logger = logging.getLogger()

    chip.set("tool", "builtin", "task", "nop", "require", ["option,file,test"],
             step="steptwo", index="0")
    chip.set("option", "file", "test", "test.txt")

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        assert node.validate() is False
    assert "Cannot resolve path test.txt in required file keypath [option,file,test]" in caplog.text


def test_summarize(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    chip.set("metric", "errors", 2, step="steptwo", index="0")
    chip.set("metric", "warnings", 4, step="steptwo", index="0")
    chip.set("metric", "tasktime", 12.5, step="steptwo", index="0")

    node = SchedulerNode(chip, "steptwo", "0")
    node.summarize()
    assert "Number of errors: 2\n" in caplog.text
    assert "Number of warnings: 4\n" in caplog.text
    assert "Finished task in 12.50s\n" in caplog.text


def test_report_output_files_builtin(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    node = SchedulerNode(chip, "steptwo", "0")
    with node.runtime():
        node._SchedulerNode__report_output_files()
    assert caplog.text == ""


def test_report_output_files_missing_outputs_dir(echo_chip, caplog):
    echo_chip.logger = logging.getLogger()
    node = SchedulerNode(echo_chip, "steptwo", "0")
    with node.runtime():
        with pytest.raises(SystemExit):
            node._SchedulerNode__report_output_files()
    assert "Output directory is missing" in caplog.text
    assert "Failed to write manifest for steptwo/0" in caplog.text
    assert "Halting steptwo/0 due to errors" in caplog.text


def test_report_output_files_missing_manifest(echo_chip, caplog):
    echo_chip.logger = logging.getLogger()
    node = SchedulerNode(echo_chip, "steptwo", "0")
    with node.runtime():
        os.makedirs(os.path.join(node.workdir, "outputs"), exist_ok=True)

        with pytest.raises(SystemExit):
            node._SchedulerNode__report_output_files()
    assert "Output manifest (dummy.pkg.json) is missing." in caplog.text
    assert "Halting steptwo/0 due to errors" in caplog.text


def test_report_output_files_missing_outputs(echo_chip, caplog):
    echo_chip.logger = logging.getLogger()
    echo_chip.set("tool", "echo", "task", "echo", "output", "echothis.txt",
                  step="steptwo", index="0")

    node = SchedulerNode(echo_chip, "steptwo", "0")
    with node.runtime():
        os.makedirs(os.path.join(node.workdir, "outputs"), exist_ok=True)
        echo_chip.write_manifest(node.get_manifest())

        with pytest.raises(SystemExit):
            node._SchedulerNode__report_output_files()
    assert "Expected output files are missing: echothis.txt" in caplog.text
    assert "Halting steptwo/0 due to errors" in caplog.text


def test_report_output_files_extra_outputs(echo_chip, caplog):
    echo_chip.logger = logging.getLogger()
    echo_chip.set("tool", "echo", "task", "echo", "output", "echothis.txt",
                  step="steptwo", index="0")

    node = SchedulerNode(echo_chip, "steptwo", "0")
    with node.runtime():
        os.makedirs(os.path.join(node.workdir, "outputs"), exist_ok=True)
        echo_chip.write_manifest(node.get_manifest())

        with open(os.path.join(node.workdir, "outputs", "echothis.txt"), 'w') as f:
            f.write("test")
        with open(os.path.join(node.workdir, "outputs", "extra.txt"), 'w') as f:
            f.write("test")

        with pytest.raises(SystemExit):
            node._SchedulerNode__report_output_files()
    assert "Unexpected output files found: extra.txt" in caplog.text
    assert "Halting steptwo/0 due to errors" in caplog.text


def test_report_output_files_extra_outputs_not_strict(echo_chip, caplog):
    echo_chip.logger = logging.getLogger()
    echo_chip.set("tool", "echo", "task", "echo", "output", "echothis.txt",
                  step="steptwo", index="0")
    echo_chip.set('option', 'strict', False)

    node = SchedulerNode(echo_chip, "steptwo", "0")
    with node.runtime():
        os.makedirs(os.path.join(node.workdir, "outputs"), exist_ok=True)
        echo_chip.write_manifest(node.get_manifest())

        with open(os.path.join(node.workdir, "outputs", "echothis.txt"), 'w') as f:
            f.write("test")
        with open(os.path.join(node.workdir, "outputs", "extra.txt"), 'w') as f:
            f.write("test")

        node._SchedulerNode__report_output_files()
    assert "Unexpected output files found: extra.txt" in caplog.text
    assert "Halting steptwo/0 due to errors" not in caplog.text


def test_run_pass(chip):
    node = SchedulerNode(chip, "stepone", "0")
    node.task.setup_work_directory(node.workdir)
    with patch("siliconcompiler.record.RecordSchema.record_userinformation") as call_track, \
         patch("siliconcompiler.record.RecordSchema.record_version") as call_version, \
         patch("siliconcompiler.core.Chip.hash_files") as call_hash:
        node.run()
        call_track.assert_not_called()
        call_version.assert_called_once()
        call_hash.assert_not_called()

    assert chip.get("metric", "tasktime", step="stepone", index="0") is not None
    assert chip.get("metric", "totaltime", step="stepone", index="0") is not None
    assert chip.get("record", "status", step="stepone", index="0") == NodeStatus.SUCCESS


def test_run_pass_record(chip):
    chip.set("option", "track", True)

    node = SchedulerNode(chip, "stepone", "0")
    node.task.setup_work_directory(node.workdir)

    with patch("siliconcompiler.record.RecordSchema.record_userinformation") as call_track, \
         patch("siliconcompiler.record.RecordSchema.record_version") as call_version, \
         patch("siliconcompiler.core.Chip.hash_files") as call_hash:
        node.run()
        call_track.assert_called_once()
        call_version.assert_called_once()
        call_hash.assert_not_called()

    assert chip.get("metric", "tasktime", step="stepone", index="0") is not None
    assert chip.get("metric", "totaltime", step="stepone", index="0") is not None
    assert chip.get("record", "status", step="stepone", index="0") == NodeStatus.SUCCESS


def test_run_pass_hash(chip):
    chip.set("option", "hash", True)

    node = SchedulerNode(chip, "stepone", "0")
    node.task.setup_work_directory(node.workdir)

    with patch("siliconcompiler.record.RecordSchema.record_userinformation") as call_track, \
         patch("siliconcompiler.record.RecordSchema.record_version") as call_version, \
         patch("siliconcompiler.core.Chip.hash_files") as call_hash:
        node.run()
        call_track.assert_not_called()
        call_version.assert_called_once()
        call_hash.assert_called()

    assert chip.get("metric", "tasktime", step="stepone", index="0") is not None
    assert chip.get("metric", "totaltime", step="stepone", index="0") is not None
    assert chip.get("record", "status", step="stepone", index="0") == NodeStatus.SUCCESS


def test_run_failed_to_validate(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    node = SchedulerNode(chip, "stepone", "0")
    node.task.setup_work_directory(node.workdir)

    with patch("siliconcompiler.scheduler.schedulernode.SchedulerNode.validate") as call_validate:
        call_validate.return_value = False
        with pytest.raises(SystemExit):
            node.run()
        call_validate.assert_called_once()

    assert chip.get("metric", "tasktime", step="stepone", index="0") is None
    assert chip.get("metric", "totaltime", step="stepone", index="0") is None
    assert chip.get("record", "status", step="stepone", index="0") == NodeStatus.ERROR

    assert "Failed to validate node setup. See previous errors" in caplog.text
    assert "Halting stepone/0 due to errors" in caplog.text


def test_run_failed_select_input(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    node = SchedulerNode(chip, "steptwo", "0")
    node.task.setup_work_directory(node.workdir)

    with patch("siliconcompiler.tool.TaskSchemaTmp.select_input_nodes") as call_input_select:
        call_input_select.return_value = []
        with pytest.raises(SystemExit):
            node.run()
        call_input_select.assert_called_once()

    assert chip.get("metric", "tasktime", step="steptwo", index="0") is None
    assert chip.get("metric", "totaltime", step="steptwo", index="0") is None
    assert chip.get("record", "status", step="steptwo", index="0") == NodeStatus.ERROR

    assert "No inputs selected for steptwo/0" in caplog.text
    assert "Halting steptwo/0 due to errors" in caplog.text


def test_run_failed_to_execute(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    node = SchedulerNode(chip, "stepone", "0")
    node.task.setup_work_directory(node.workdir)

    with patch("siliconcompiler.scheduler.schedulernode.SchedulerNode.execute") as call_exec:
        call_exec.side_effect = ValueError("thiserrorisraised")
        with pytest.raises(SystemExit):
            node.run()
        call_exec.assert_called_once()

    assert chip.get("metric", "tasktime", step="stepone", index="0") is None
    assert chip.get("metric", "totaltime", step="stepone", index="0") is None
    assert chip.get("record", "status", step="stepone", index="0") == NodeStatus.ERROR

    assert "thiserrorisraised" in caplog.text
    assert "Halting stepone/0 due to errors" in caplog.text


def test_run_without_queue(chip):
    node = SchedulerNode(chip, "stepone", "0")
    node.task.setup_work_directory(node.workdir)
    with patch("logging.Logger.removeHandler") as call_remove_logger, \
         patch("siliconcompiler.scheduler.schedulernode.SchedulerNode.execute") as call_exec:
        node.run()
        call_exec.assert_called_once()
        call_remove_logger.assert_not_called()


def test_run_with_queue(chip):
    node = SchedulerNode(chip, "stepone", "0")

    class DummyPipe:
        calls = 0

        def send(self, *args, **kwargs):
            self.calls += 1
    pipe = DummyPipe()
    node.set_queue(pipe, Queue())

    node.task.setup_work_directory(node.workdir)
    with patch("logging.Logger.removeHandler") as call_remove_logger, \
         patch("siliconcompiler.scheduler.schedulernode.SchedulerNode.execute") as call_exec:
        node.run()
        call_exec.assert_called_once()
        call_remove_logger.assert_called_once()
        assert pipe.calls == 1


def test_run_called_testcase_on_error(chip):
    node = SchedulerNode(chip, "stepone", "0")
    assert node._SchedulerNode__generate_test_case is True

    node.task.setup_work_directory(node.workdir)
    node._SchedulerNode__error = True

    with patch("siliconcompiler.scheduler.schedulernode.SchedulerNode."
               "_SchedulerNode__generate_testcase") as call_testcase:
        with pytest.raises(SystemExit):
            node.run()
        call_testcase.assert_called_once()


def test_run_not_called_testcase_on_error(chip):
    node = SchedulerNode(chip, "stepone", "0", replay=True)
    assert node._SchedulerNode__generate_test_case is False

    node.task.setup_work_directory(node.workdir)
    node._SchedulerNode__error = True

    with patch("siliconcompiler.scheduler.schedulernode.SchedulerNode."
               "_SchedulerNode__generate_testcase") as call_testcase:
        with pytest.raises(SystemExit):
            node.run()
        call_testcase.assert_not_called()


def test_copy_from_do_nothing(chip, caplog):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    node = SchedulerNode(chip, "stepone", "0")
    node.copy_from("test")
    assert caplog.text == ""


def test_copy_from(chip, caplog, has_graphviz):
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    node = SchedulerNode(chip, "stepone", "0")
    with node.runtime():
        node.task.setup_work_directory(node.workdir)
        node.task.generate_replay_script(node.replay_script, node.workdir)
        chip.write_flowgraph(node.get_manifest("input"))
        chip.write_flowgraph(node.get_manifest("output"))

    chip.set("option", "jobname", "newname")
    node = SchedulerNode(chip, "stepone", "0")

    assert not os.path.exists(node.replay_script)
    assert not os.path.exists(node.get_manifest("input"))
    assert not os.path.exists(node.get_manifest("output"))

    node.copy_from("job0")
    assert "Importing stepone/0 from job0" in caplog.text

    assert os.path.exists(node.replay_script)
    with open(node.replay_script, "r") as f:
        assert "job0" not in f.read()

    assert os.path.exists(node.get_manifest("input"))
    input_schema = Schema.from_manifest(filepath=node.get_manifest("input"))
    assert input_schema.get("option", "jobname") == "newname"

    assert os.path.exists(node.get_manifest("output"))
    output_schema = Schema.from_manifest(filepath=node.get_manifest("output"))
    assert output_schema.get("option", "jobname") == "newname"
