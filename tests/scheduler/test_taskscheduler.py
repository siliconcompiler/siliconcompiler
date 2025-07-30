import pytest

from threading import Lock

from siliconcompiler import NodeStatus
from siliconcompiler import Chip, Flow
from siliconcompiler.scheduler import TaskScheduler
from siliconcompiler.scheduler.taskscheduler import utils as imported_utils
from siliconcompiler.scheduler import SchedulerNode

from siliconcompiler.tools.builtin import join, nop


@pytest.fixture
def large_flow():
    flow = Flow("testflow")

    flow.node("testflow", "joinone", join)
    for n in range(3):
        flow.node("testflow", "stepone", nop, index=n)
        flow.edge("testflow", "stepone", "joinone", tail_index=n)

    flow.node("testflow", "jointwo", join)
    for n in range(3):
        flow.node("testflow", "steptwo", nop, index=n)

        flow.edge("testflow", "joinone", "steptwo", head_index=n)
        flow.edge("testflow", "steptwo", "jointwo", tail_index=n)

    flow.node("testflow", "jointhree", join)
    for n in range(3):
        flow.node("testflow", "stepthree", nop, index=n)

        flow.edge("testflow", "jointwo", "stepthree", head_index=n)
        flow.edge("testflow", "stepthree", "jointhree", tail_index=n)

    chip = Chip('testdesign')
    chip.use(flow)
    chip.set("option", "flow", "testflow")

    chip.set("tool", "builtin", "task", "nop", "threads", 1)
    for step, index in chip.get("flowgraph", "testflow", field="schema").get_nodes():
        SchedulerNode(chip, step, index).setup()
        chip.set("record", "status", NodeStatus.PENDING, step=step, index=index)

    return chip


@pytest.fixture
def make_tasks():
    def make(chip):
        tasks = {}
        for step, index in chip.get(
                "flowgraph", chip.get('option', 'flow'), field="schema").get_nodes():
            tasks[(step, index)] = SchedulerNode(chip, step, index)
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
    with pytest.raises(ValueError, match="pre_run0 is not a valid callback"):
        TaskScheduler.register_callback("pre_run0", lambda: None)


def test_register_callback():
    def callback(chip):
        pass

    callbacks = TaskScheduler._TaskScheduler__callbacks
    assert callbacks["pre_run"] is not callback
    TaskScheduler.register_callback("pre_run", callback)
    assert callbacks["pre_run"] is callback


def test_run(large_flow, make_tasks):
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    scheduler.run()

    for step, index in large_flow.get("flowgraph", "testflow", field="schema").get_nodes():
        assert large_flow.get("record", "status", step=step, index=index) == NodeStatus.SUCCESS


def test_run_callbacks(large_flow, make_tasks):
    class Callback:
        pre_run = 0
        pre_node = 0
        post_node = 0
        post_run = 0

        @staticmethod
        def callback_pre_run(chip):
            Callback.pre_run += 1

        @staticmethod
        def callback_pre_node(chip, step, index):
            Callback.pre_node += 1

        @staticmethod
        def callback_post_node(chip, step, index):
            Callback.post_node += 1

        @staticmethod
        def callback_post_run(chip):
            Callback.post_run += 1

    TaskScheduler.register_callback("pre_run", Callback.callback_pre_run)
    TaskScheduler.register_callback("pre_node", Callback.callback_pre_node)
    TaskScheduler.register_callback("post_node", Callback.callback_post_node)
    TaskScheduler.register_callback("post_run", Callback.callback_post_run)

    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    scheduler.run()

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

    large_flow._dash = FakeDashboard()

    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    scheduler.run()

    assert len(large_flow._dash.calls) == 14
    assert large_flow._dash.calls[0] is None
    assert all(["starttimes" in c for c in large_flow._dash.calls[1:]])
    assert len(large_flow._dash.calls[-1]["starttimes"]) == 13


def test_run_control_c(large_flow, make_tasks, monkeypatch):
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    def dummy_loop():
        raise KeyboardInterrupt
    monkeypatch.setattr(scheduler, "_TaskScheduler__run_loop", dummy_loop)

    with pytest.raises(SystemExit):
        scheduler.run()


def test_check(large_flow, make_tasks):
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    large_flow.set("record", "status", NodeStatus.SUCCESS, step="jointhree", index="0")
    scheduler.check()


def test_check_invalid(large_flow, make_tasks):
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    with pytest.raises(RuntimeError, match="These final steps could not be reached: jointhree"):
        scheduler.check()
