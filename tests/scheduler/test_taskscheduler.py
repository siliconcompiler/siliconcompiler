import logging

import pytest

from threading import Lock

from siliconcompiler import NodeStatus
from siliconcompiler import Project, Flowgraph, Design
from siliconcompiler.scheduler import TaskScheduler
from siliconcompiler.scheduler.taskscheduler import utils as imported_utils
from siliconcompiler.scheduler import SchedulerNode

from siliconcompiler.tools.builtin.nop import NOPTask
from siliconcompiler.tools.builtin.join import JoinTask


@pytest.fixture
def large_flow():
    flow = Flowgraph("testflow")

    flow.node("joinone", JoinTask())
    for n in range(3):
        flow.node("stepone", NOPTask(), index=n)
        flow.edge("stepone", "joinone", tail_index=n)

    flow.node("jointwo", JoinTask())
    for n in range(3):
        flow.node("steptwo", NOPTask(), index=n)

        flow.edge("joinone", "steptwo", head_index=n)
        flow.edge("steptwo", "jointwo", tail_index=n)

    flow.node("jointhree", JoinTask())
    for n in range(3):
        flow.node("stepthree", NOPTask(), index=n)

        flow.edge("jointwo", "stepthree", head_index=n)
        flow.edge("stepthree", "jointhree", tail_index=n)

    design = Design("testdesign")
    with design.active_fileset("rtl"):
        design.set_topmodule("top")

    proj = Project(design)
    proj.add_fileset("rtl")
    proj.set_flow(flow)

    for step, index in flow.get_nodes():
        SchedulerNode(proj, step, index).setup()
        proj.set("record", "status", NodeStatus.PENDING, step=step, index=index)

    return proj


@pytest.fixture
def make_tasks():
    def make(proj):
        tasks = {}
        for step, index in proj.get(
                "flowgraph", proj.get('option', 'flow'), field="schema").get_nodes():
            tasks[(step, index)] = SchedulerNode(proj, step, index)
        return tasks
    return make


def test_get_nodes(large_flow, make_tasks):
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    assert scheduler.get_nodes() == [
        ('joinone', '0'), ('jointhree', '0'), ('jointwo', '0'),
        ('stepone', '0'), ('stepone', '1'), ('stepone', '2'),
        ('stepthree', '0'), ('stepthree', '1'), ('stepthree', '2'),
        ('steptwo', '0'), ('steptwo', '1'), ('steptwo', '2')]


def test_get_nodes_with_complete(large_flow, make_tasks):
    large_flow.set("record", "status", NodeStatus.SUCCESS, step="stepone", index="0")
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    assert scheduler.get_nodes() == [
        ('joinone', '0'), ('jointhree', '0'), ('jointwo', '0'),
        ('stepone', '1'), ('stepone', '2'),
        ('stepthree', '0'), ('stepthree', '1'), ('stepthree', '2'),
        ('steptwo', '0'), ('steptwo', '1'), ('steptwo', '2')]


def test_register_callback_invalid():
    with pytest.raises(ValueError, match="^pre_run0 is not a valid callback$"):
        TaskScheduler.register_callback("pre_run0", lambda: None)


def test_register_callback():
    def callback(proj):
        pass

    callbacks = TaskScheduler._TaskScheduler__callbacks
    assert callbacks["pre_run"] is not callback
    TaskScheduler.register_callback("pre_run", callback)
    assert callbacks["pre_run"] is callback


def test_run(large_flow, make_tasks):
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    scheduler.run(logging.NullHandler())

    for step, index in large_flow.get("flowgraph", "testflow", field="schema").get_nodes():
        assert large_flow.get("record", "status", step=step, index=index) == NodeStatus.SUCCESS


def test_run_callbacks(large_flow, make_tasks):
    class Callback:
        pre_run = 0
        pre_node = 0
        post_node = 0
        post_run = 0

        @staticmethod
        def callback_pre_run(proj):
            Callback.pre_run += 1

        @staticmethod
        def callback_pre_node(proj, step, index):
            Callback.pre_node += 1

        @staticmethod
        def callback_post_node(proj, step, index):
            Callback.post_node += 1

        @staticmethod
        def callback_post_run(proj):
            Callback.post_run += 1

    TaskScheduler.register_callback("pre_run", Callback.callback_pre_run)
    TaskScheduler.register_callback("pre_node", Callback.callback_pre_node)
    TaskScheduler.register_callback("post_node", Callback.callback_post_node)
    TaskScheduler.register_callback("post_run", Callback.callback_post_run)

    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    scheduler.run(logging.NullHandler())

    assert Callback.pre_run == 1
    assert Callback.pre_node == 12
    assert Callback.post_node == 12
    assert Callback.post_run == 1


def test_run_dashboard(large_flow, make_tasks, monkeypatch):
    class FakeDashboard:
        lock = Lock()
        calls = []

        def update_manifest(self, payload=None):
            with self.lock:
                self.calls.append(payload)

    def dummy_get_cores(*args, **kwargs):
        return 1
    monkeypatch.setattr(imported_utils, "get_cores", dummy_get_cores)

    dashboard = FakeDashboard()
    large_flow._Project__dashboard = dashboard

    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    scheduler.run(logging.NullHandler())

    assert len(dashboard.calls) == 14
    assert dashboard.calls[0] is None
    assert all(["starttimes" in c for c in dashboard.calls[1:]])
    assert len(dashboard.calls[-1]["starttimes"]) == 13


def test_run_control_c(large_flow, make_tasks, monkeypatch):
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    def dummy_loop():
        raise KeyboardInterrupt
    monkeypatch.setattr(scheduler, "_TaskScheduler__run_loop", dummy_loop)

    with pytest.raises(SystemExit):
        scheduler.run(logging.NullHandler())


def test_check(large_flow, make_tasks):
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    large_flow.set("record", "status", NodeStatus.SUCCESS, step="jointhree", index="0")
    scheduler.check()


def test_check_invalid(large_flow, make_tasks):
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    with pytest.raises(RuntimeError, match="^These final steps could not be reached: jointhree$"):
        scheduler.check()
