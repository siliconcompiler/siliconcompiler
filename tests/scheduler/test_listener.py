import logging

import pytest

from siliconcompiler import Project, Design
from siliconcompiler.scheduler.listener import RunListener, RunListeners


class Recorder(RunListener):
    def __init__(self):
        self.events = []

    def run_started(self, project):
        self.events.append(("run_started",))

    def flow_started(self, project):
        self.events.append(("flow_started",))

    def node_started(self, project, step, index):
        self.events.append(("node_started", step, index))

    def node_finished(self, project, step, index):
        self.events.append(("node_finished", step, index))

    def flow_finished(self, project, error):
        self.events.append(("flow_finished", error))

    def run_finished(self, project, error):
        self.events.append(("run_finished", error))


class Broken(RunListener):
    def run_started(self, project):
        raise ValueError("listener broke")

    def flow_started(self, project):
        raise ValueError("listener broke")

    def node_started(self, project, step, index):
        raise ValueError("listener broke")

    def node_finished(self, project, step, index):
        raise ValueError("listener broke")

    def flow_finished(self, project, error):
        raise ValueError("listener broke")

    def run_finished(self, project, error):
        raise ValueError("listener broke")


@pytest.fixture
def project(project_logger):
    proj = Project(Design("testdesign"))
    project_logger(proj)
    return proj


def test_run_listener_does_nothing(project):
    """The base listener accepts every event and does nothing with it."""
    listener = RunListener()
    listener.run_started(project)
    listener.flow_started(project)
    listener.node_started(project, "step", "0")
    listener.node_finished(project, "step", "0")
    listener.flow_finished(project, None)
    listener.run_finished(project, None)


def test_run_listeners_forwards_in_order(project):
    """Each event reaches every listener, in the order they were given."""
    first, second = Recorder(), Recorder()
    listeners = RunListeners([first, second])

    error = ValueError("ended")
    listeners.run_started(project)
    listeners.flow_started(project)
    listeners.node_started(project, "step", "0")
    listeners.node_finished(project, "step", "0")
    listeners.flow_finished(project, error)
    listeners.run_finished(project, error)

    expected = [("run_started",), ("flow_started",), ("node_started", "step", "0"),
                ("node_finished", "step", "0"), ("flow_finished", error),
                ("run_finished", error)]
    assert first.events == expected
    assert second.events == expected


@pytest.mark.parametrize("event,args", [
    ("run_started", ()),
    ("flow_started", ()),
    ("node_started", ("step", "0")),
    ("node_finished", ("step", "0")),
    ("flow_finished", (None,)),
    ("run_finished", (None,))])
def test_run_listeners_logs_a_failing_listener(project, caplog, event, args):
    """A listener that raises is logged, and the listeners after it still hear the event."""
    after = Recorder()
    listeners = RunListeners([Broken(), after])

    with caplog.at_level(logging.ERROR):
        getattr(listeners, event)(project, *args)

    assert f"Broken.{event}() failed: listener broke" in caplog.text
    assert after.events == [(event, *args)]


def test_run_listeners_lets_interrupts_through(project):
    """An interrupt raised by a listener stops the run, as it would anywhere else."""
    class Interrupted(RunListener):
        def flow_started(self, project):
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        RunListeners([Interrupted()]).flow_started(project)
