import logging

import pytest

from threading import Lock
from unittest.mock import MagicMock

from siliconcompiler.utils.multiprocessing import MPManager
from siliconcompiler import NodeStatus
from siliconcompiler import Project, Flowgraph, Design
from siliconcompiler.scheduler import TaskScheduler
from siliconcompiler.scheduler import taskscheduler as taskscheduler_module
from siliconcompiler.scheduler.taskscheduler import utils as imported_utils
from siliconcompiler.scheduler import SchedulerNode, SCRuntimeError

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
        ('stepone', '0'), ('stepone', '1'), ('stepone', '2'),
        ('joinone', '0'),
        ('steptwo', '0'), ('steptwo', '1'), ('steptwo', '2'),
        ('jointwo', '0'),
        ('stepthree', '0'), ('stepthree', '1'), ('stepthree', '2'),
        ('jointhree', '0')]


def test_get_nodes_with_complete(large_flow, make_tasks):
    large_flow.set("record", "status", NodeStatus.SUCCESS, step="stepone", index="0")
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    assert scheduler.get_nodes() == [
        ('stepone', '1'), ('stepone', '2'),
        ('joinone', '0'),
        ('steptwo', '0'), ('steptwo', '1'), ('steptwo', '2'),
        ('jointwo', '0'),
        ('stepthree', '0'), ('stepthree', '1'), ('stepthree', '2'),
        ('jointhree', '0')]


def test_register_callback_invalid():
    with pytest.raises(ValueError, match=r"^pre_run0 is not a valid callback$"):
        TaskScheduler.register_callback("pre_run0", lambda: None)


def test_register_callback():
    def callback(proj):
        pass

    settings = MPManager().get_transient_settings()
    assert "pre_run" not in settings.get_category('TaskScheduler')
    TaskScheduler.register_callback("pre_run", callback)
    assert settings.get('TaskScheduler', "pre_run") is callback


@pytest.mark.timeout(180)
def test_run(large_flow, make_tasks):
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    scheduler.run(logging.NullHandler())

    for step, index in large_flow.get("flowgraph", "testflow", field="schema").get_nodes():
        assert large_flow.get("record", "status", step=step, index=index) == NodeStatus.SUCCESS


@pytest.mark.timeout(180)
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


@pytest.mark.timeout(180)
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


def test_run_control_c_stops_log_listener_once(large_flow, make_tasks, monkeypatch):
    '''On KeyboardInterrupt, the QueueListener must be stopped exactly once.
    Calling stop() twice raises AttributeError once the listener thread has
    been joined; before this fix the except branch stopped it eagerly and
    the finally block stopped it again.'''
    stop_calls = []

    class FakeQueueListener:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

        def stop(self):
            stop_calls.append(True)

    monkeypatch.setattr(taskscheduler_module, "QueueListener", FakeQueueListener)

    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    def dummy_loop():
        raise KeyboardInterrupt
    monkeypatch.setattr(scheduler, "_TaskScheduler__run_loop", dummy_loop)

    with pytest.raises(SystemExit):
        scheduler.run(logging.NullHandler())

    assert len(stop_calls) == 1, \
        f"QueueListener.stop() must be called once, got {len(stop_calls)}"


def test_run_log_listener_stop_tolerates_dead_queue(large_flow, make_tasks, monkeypatch):
    '''If the SyncManager-backed log queue has already gone away by the time
    the finally block runs (e.g. during an interrupted shutdown), stop()
    raising OSError/EOFError/BrokenPipeError must not escape run().'''
    class DeadQueueListener:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

        def stop(self):
            raise BrokenPipeError("queue gone")

    monkeypatch.setattr(taskscheduler_module, "QueueListener", DeadQueueListener)

    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    def dummy_loop():
        return None
    monkeypatch.setattr(scheduler, "_TaskScheduler__run_loop", dummy_loop)

    # Must not raise.
    scheduler.run(logging.NullHandler())


def _setup_completed_node(scheduler, node, exitcode, *, pipe_has_data=False):
    '''Helper: mark a node as running with a fake process that has already
    exited. Returns the mocks so the test can inspect call args.'''
    info = scheduler._TaskScheduler__nodes[node]
    proc = MagicMock()
    proc.is_alive.return_value = False
    proc.exitcode = exitcode
    info["proc"] = proc
    info["running"] = True

    pipe = MagicMock()
    pipe.poll.return_value = pipe_has_data
    pipe.recv.return_value = {}
    info["parent_pipe"] = pipe
    return proc, pipe


def test_process_completed_nodes_uses_nonblocking_poll(large_flow, make_tasks):
    '''The scheduler must not block waiting on a child's pipe after the child
    has already exited. poll() should be called with a 0 (or no) timeout.'''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    node = ("stepone", "0")
    _, pipe = _setup_completed_node(scheduler, node, exitcode=0)

    scheduler._TaskScheduler__process_completed_nodes()

    assert pipe.poll.called
    # poll() may be called with a positional timeout or none at all; the
    # only forbidden value is the previous 1-second blocking timeout.
    for call in pipe.poll.call_args_list:
        args, kwargs = call
        timeout = args[0] if args else kwargs.get("timeout", 0)
        assert timeout == 0, f"poll() was called with a blocking timeout: {timeout!r}"


def test_process_completed_nodes_signal_killed_is_error(large_flow, make_tasks):
    '''A child terminated by a signal reports a negative exitcode. The status
    record has not been updated by such a child, so the scheduler must
    classify the node as ERROR rather than trusting the stale record.'''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    node = ("stepone", "0")
    # Force a stale "SUCCESS" status that a real SIGKILLed child could not
    # have written. The fix must override this.
    large_flow.set("record", "status", NodeStatus.SUCCESS,
                   step=node[0], index=node[1])
    _setup_completed_node(scheduler, node, exitcode=-9)

    scheduler._TaskScheduler__process_completed_nodes()

    assert large_flow.get("record", "status",
                          step=node[0], index=node[1]) == NodeStatus.ERROR


def test_process_completed_nodes_clean_exit_keeps_status(large_flow, make_tasks):
    '''Regression guard: a clean (exitcode == 0) exit must continue to
    preserve whatever status the child wrote into the record.'''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    node = ("stepone", "0")
    large_flow.set("record", "status", NodeStatus.SUCCESS,
                   step=node[0], index=node[1])
    _setup_completed_node(scheduler, node, exitcode=0)

    scheduler._TaskScheduler__process_completed_nodes()

    assert large_flow.get("record", "status",
                          step=node[0], index=node[1]) == NodeStatus.SUCCESS


def test_process_completed_nodes_nonzero_exit_is_error(large_flow, make_tasks):
    '''A positive nonzero exit (e.g. sys.exit(1) from halt()) must still be
    classified as ERROR. This existed before the signal fix but the
    rewritten comparison (!= 0) needs explicit coverage too.'''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    node = ("stepone", "0")
    _setup_completed_node(scheduler, node, exitcode=1)

    scheduler._TaskScheduler__process_completed_nodes()

    assert large_flow.get("record", "status",
                          step=node[0], index=node[1]) == NodeStatus.ERROR


def test_check(large_flow, make_tasks):
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    large_flow.set("record", "status", NodeStatus.SUCCESS, step="jointhree", index="0")
    scheduler.check()


def test_check_invalid(large_flow, make_tasks):
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    with pytest.raises(SCRuntimeError, match=r"^Could not run final steps: jointhree$"):
        scheduler.check()


def test_check_invalid_with_error(large_flow, make_tasks):
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    large_flow.set("record", "status", "error", step="stepone", index=0)
    large_flow.set("record", "status", "error", step="stepone", index=1)

    with pytest.raises(SCRuntimeError,
                       match=r"^Could not run final steps \(jointhree\) due to errors "
                             r"in: stepone/0, stepone/1$"):
        scheduler.check()
