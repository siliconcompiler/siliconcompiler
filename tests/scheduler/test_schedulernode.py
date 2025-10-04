import os
import logging
import pytest

from scheduler.schedulernode import SchedulerNode, SchedulerFlowReset, TaskSkip


def test_setup_error(project, monkeypatch, caplog):
    _ = project
    _ = monkeypatch
    _ = caplog

    def dummy_setup(*_args, **_kwargs):
        raise ValueError()


def test_setup_with_return(project, monkeypatch, caplog):
    _ = project
    _ = monkeypatch
    _ = caplog

    def dummy_setup(*_args, **_kwargs):
        return "This should not be there"


def test_setup_skipped(project, monkeypatch, caplog):
    _ = project
    _ = monkeypatch
    _ = caplog

    def dummy_setup(*_args, **_kwargs):
        raise TaskSkip()


def test_check_previous_run_status_flow(project):
    _ = project
    node = SchedulerNode(project, "stepone", "0")
    node_other = SchedulerNode(project, "steptwo", "0")
    with pytest.raises(SchedulerFlowReset,
                       match=r"^Flow name changed, require full reset$"):
        node.check_previous_run_status(node_other)


def test_schedulerflowreset_exception_attributes():
    # Test it can be caught via pytest
    with pytest.raises(SchedulerFlowReset) as e_info:
        raise SchedulerFlowReset("Test message")
    assert str(e_info.value) == "Test message"


def test_check_previous_run_status_inputs_changed(project, monkeypatch, caplog):
    _ = project
    _ = monkeypatch
    _ = caplog

    def dummy_select(*_args, **_kwargs):
        return [("test", "1")]


def test_check_previous_run_status_no_change(project, monkeypatch):
    _ = project
    _ = monkeypatch

    def dummy_select(*_args, **_kwargs):
        return [("stepone", "0")]


def test_requires_run_all_pass(project, monkeypatch):
    _ = project
    _ = monkeypatch

    def dummy_get_check_changed_keys(*_args):
        return (set(), set())

    def dummy_check_previous_run_status(*_args):
        return True


def test_run_pass_restore_env(project):
    _ = project

    def check_run(*_args, **_kwargs):
        assert "TEST" in os.environ
        assert "THISVALUE" == os.environ["TEST"]
        return 0


def test_run_with_queue(project):
    _ = project

    class DummyPipe:
        calls = 0

        def send(self, *args, **kwargs):
            self.calls += 1


def test_copy_from(project, monkeypatch, caplog):
    _ = caplog
    monkeypatch.setattr(project, "_Project__logger", logging.getLogger())
    project.logger.setLevel(logging.INFO)