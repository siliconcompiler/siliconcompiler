import logging
import multiprocessing

import pytest

from threading import Lock
from unittest.mock import MagicMock

from siliconcompiler.utils.multiprocessing import MPManager, get_process_context
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


def test_log_queue_matches_start_method(large_flow, make_tasks):
    """The per-scheduler log queue must be fork-safe for the active start method.

    Under ``fork`` a node worker inherits the parent's live SyncManager socket
    connection; a manager-backed queue then has the worker's put() and the
    parent's QueueListener get() drive the *same* inherited connection from two
    processes at once, corrupting the manager's framed protocol and deadlocking
    the run. So on the fork path the queue must be a plain pipe-backed
    multiprocessing queue. Spawn/forkserver cannot inherit fds and need the
    picklable manager queue (reconnected fresh per worker, hence safe).

    This runs on every OS and asserts whichever choice this platform's start
    method requires.
    """
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    log_queue = scheduler._TaskScheduler__log_queue

    if get_process_context().get_start_method() == "fork":
        assert type(log_queue).__module__ == "multiprocessing.queues", \
            f"fork log queue must be a plain multiprocessing queue (a manager " \
            f"proxy deadlocks across fork), got {type(log_queue)!r}"
    else:
        # spawn / forkserver: a picklable manager queue is required and safe.
        assert type(log_queue).__module__ == "multiprocessing.managers", \
            f"spawn log queue must be a picklable manager queue, " \
            f"got {type(log_queue)!r}"


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="fork start method not available on this platform (e.g. Windows)")
def test_log_queue_is_plain_on_fork(large_flow, make_tasks, monkeypatch):
    """Force the fork path and assert a plain, non-manager queue is chosen.

    Complements ``test_log_queue_matches_start_method`` by exercising the
    fork-safety invariant even on platforms whose *default* start method is not
    fork (macOS), so a regression that reintroduces a manager-backed queue on
    the fork path is caught on both Linux and macOS CI. Only the queue-selection
    logic is exercised -- no worker is actually forked.
    """
    fork_ctx = multiprocessing.get_context("fork")
    monkeypatch.setattr(taskscheduler_module, "get_process_context",
                        lambda: fork_ctx)

    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    log_queue = scheduler._TaskScheduler__log_queue

    assert type(log_queue).__module__ != "multiprocessing.managers", \
        f"fork path must not select a SyncManager proxy queue, " \
        f"got {type(log_queue)!r}"
    assert type(log_queue).__module__ == "multiprocessing.queues", \
        f"fork path must select a plain multiprocessing queue, " \
        f"got {type(log_queue)!r}"


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


@pytest.mark.parametrize("exc", [
    BrokenPipeError("queue gone"),
    ConnectionResetError("reset"),
    EOFError("eof"),
    OSError("oserr"),
    taskscheduler_module.RemoteError("remote"),
])
def test_run_log_listener_stop_tolerates_dead_queue(large_flow, make_tasks,
                                                    monkeypatch, exc):
    '''If the SyncManager-backed log queue has already gone away by the time
    the finally block runs (e.g. during an interrupted shutdown), the
    exceptions that QueueListener.stop()'s sentinel put may raise must not
    escape run(). The caught set mirrors MPQueueHandler.enqueue.'''
    class DeadQueueListener:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

        def stop(self):
            raise exc

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


# ---------------------------------------------------------------------------
# Breakpoint scheduling
#
# A node with a breakpoint must execute in complete isolation: it takes
# priority over ordinary nodes, only starts once nothing else is running, and
# blocks all other launches until it finishes. When several breakpoints are
# ready at once they run one at a time in flowgraph execution order.
#
# The tests below drive the private scheduling primitives directly with mocked
# processes so the launch decisions are fully deterministic (no subprocess
# timing involved), plus a couple of real end-to-end runs to guard against the
# wiring breaking.
# ---------------------------------------------------------------------------


def _set_breakpoints(proj, *nodes):
    '''Set a breakpoint option on each (step, index) before scheduler build.'''
    for step, index in nodes:
        proj.option.set_breakpoint(True, step=step, index=str(index))


def _mock_all_procs(scheduler, *, alive=True, threads=1):
    '''Replace every node's real Process with a controllable MagicMock and
    normalize per-node thread counts so resource gating is deterministic.

    Returns a dict mapping (step, index) -> proc mock.'''
    procs = {}
    nodes = scheduler._TaskScheduler__nodes
    for node, info in nodes.items():
        proc = MagicMock()
        proc.is_alive.return_value = alive
        proc.exitcode = 0
        info["proc"] = proc
        info["threads"] = threads
        procs[node] = proc
    return procs


def _set_resources(scheduler, max_parallel):
    '''Pin the resource limits so launch decisions depend only on the count of
    parallel jobs, never on the host's actual core count.'''
    scheduler._TaskScheduler__max_parallel_run = max_parallel
    scheduler._TaskScheduler__max_cores = 10_000
    scheduler._TaskScheduler__max_threads = 10_000


def _launch(scheduler):
    return scheduler._TaskScheduler__launch_nodes()


def _mark_done(scheduler, proj, node, status=NodeStatus.SUCCESS):
    '''Simulate a running node finishing: flip its mocked process to dead,
    write the resulting record status, and run the completion handler so the
    scheduler clears its running/proc state exactly as it would in a real run.'''
    info = scheduler._TaskScheduler__nodes[node]
    info["proc"].is_alive.return_value = False
    info["proc"].exitcode = 0
    proj.set("record", "status", status, step=node[0], index=node[1])
    scheduler._TaskScheduler__process_completed_nodes()


def test_breakpoint_flag_detected(large_flow, make_tasks):
    '''The breakpoint option must be captured per-node at construction.'''
    _set_breakpoints(large_flow, ("steptwo", "1"))
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    nodes = scheduler._TaskScheduler__nodes
    assert nodes[("steptwo", "1")]["breakpoint"] is True
    assert all(info["breakpoint"] is False
               for node, info in nodes.items() if node != ("steptwo", "1"))


def test_breakpoint_launches_alone_when_idle(large_flow, make_tasks):
    '''With the machine idle, a single breakpoint entry node launches by
    itself even though its sibling entry nodes are equally ready.'''
    _set_breakpoints(large_flow, ("stepone", "0"))
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=3)

    assert _launch(scheduler) is True
    assert scheduler.get_running_nodes() == [("stepone", "0")]


def test_breakpoint_takes_priority_over_ready_siblings(large_flow, make_tasks):
    '''Ready non-breakpoint siblings must not be co-scheduled with a ready
    breakpoint, even though resources would allow them all to run.'''
    _set_breakpoints(large_flow, ("stepone", "1"))
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=3)

    _launch(scheduler)
    # Only the breakpoint runs; the other two ready entry nodes are held back.
    assert scheduler.get_running_nodes() == [("stepone", "1")]


def test_nothing_launches_while_breakpoint_running(large_flow, make_tasks):
    '''Once a breakpoint is running, no further node (breakpoint or not) may
    start until it completes.'''
    _set_breakpoints(large_flow, ("stepone", "0"))
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=3)

    _launch(scheduler)
    assert scheduler.get_running_nodes() == [("stepone", "0")]

    # The breakpoint is still alive; subsequent launch passes are no-ops.
    assert _launch(scheduler) is False
    assert scheduler.get_running_nodes() == [("stepone", "0")]


def test_breakpoint_waits_for_running_nodes_to_drain(large_flow, make_tasks):
    '''A ready breakpoint must not start while other nodes are still running,
    and it must also suppress launching any new ordinary nodes in the
    meantime (so the machine can drain to idle).'''
    _set_breakpoints(large_flow, ("stepone", "0"))
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    procs = _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=3)

    # Pretend an ordinary sibling is already running.
    info = scheduler._TaskScheduler__nodes[("stepone", "1")]
    info["running"] = True
    procs[("stepone", "1")].is_alive.return_value = True
    large_flow.set("record", "status", NodeStatus.RUNNING, step="stepone", index="1")

    # Breakpoint cannot start (something is running) and stepone/2 must be
    # held back so the machine can drain.
    assert _launch(scheduler) is False
    assert scheduler.get_running_nodes() == [("stepone", "1")]


def test_breakpoint_runs_after_drain(large_flow, make_tasks):
    '''After the last running node drains, the held breakpoint runs alone and
    the remaining ordinary sibling still waits behind it.'''
    _set_breakpoints(large_flow, ("stepone", "0"))
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    procs = _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=3)

    info = scheduler._TaskScheduler__nodes[("stepone", "1")]
    info["running"] = True
    procs[("stepone", "1")].is_alive.return_value = True
    large_flow.set("record", "status", NodeStatus.RUNNING, step="stepone", index="1")

    _launch(scheduler)
    assert scheduler.get_running_nodes() == [("stepone", "1")]

    # Drain the running sibling, then the breakpoint takes the machine alone.
    _mark_done(scheduler, large_flow, ("stepone", "1"))
    assert _launch(scheduler) is True
    assert scheduler.get_running_nodes() == [("stepone", "0")]


def test_multiple_breakpoints_run_serially_in_order(large_flow, make_tasks):
    '''Two ready breakpoints run one at a time, earliest-in-execution-order
    first, and a breakpoint always preempts a ready ordinary sibling.'''
    _set_breakpoints(large_flow, ("stepone", "0"), ("stepone", "2"))
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=3)

    # First the earliest breakpoint, alone.
    _launch(scheduler)
    assert scheduler.get_running_nodes() == [("stepone", "0")]

    _mark_done(scheduler, large_flow, ("stepone", "0"))

    # Now the second breakpoint runs alone, ahead of the ordinary stepone/1.
    assert _launch(scheduler) is True
    assert scheduler.get_running_nodes() == [("stepone", "2")]

    _mark_done(scheduler, large_flow, ("stepone", "2"))

    # Only once both breakpoints are done does the ordinary node run.
    assert _launch(scheduler) is True
    assert scheduler.get_running_nodes() == [("stepone", "1")]


def test_not_ready_breakpoint_does_not_block_others(large_flow, make_tasks):
    '''A breakpoint whose dependencies are not yet satisfied must not suppress
    ordinary nodes that are ready to run.'''
    # joinone depends on all three stepone nodes, which have not run yet.
    _set_breakpoints(large_flow, ("joinone", "0"))
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=3)

    _launch(scheduler)
    # The not-yet-ready breakpoint is irrelevant; entry nodes launch normally.
    assert scheduler.get_running_nodes() == [
        ("stepone", "0"), ("stepone", "1"), ("stepone", "2")]


def test_no_breakpoint_launches_in_parallel(large_flow, make_tasks):
    '''Sanity: without breakpoints, all ready entry nodes launch together.'''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=3)

    assert _launch(scheduler) is True
    assert scheduler.get_running_nodes() == [
        ("stepone", "0"), ("stepone", "1"), ("stepone", "2")]


def test_no_breakpoint_respects_max_parallel(large_flow, make_tasks):
    '''Sanity: the ordinary resource cap is still honored when no breakpoints
    are involved.'''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=2)

    _launch(scheduler)
    assert scheduler.get_running_nodes() == [("stepone", "0"), ("stepone", "1")]


def test_breakpoint_node_with_failed_deps_is_pruned(large_flow, make_tasks):
    '''A breakpoint node whose dependencies failed must still be pruned (its
    proc cleared) rather than waiting forever for an isolated slot.'''
    _set_breakpoints(large_flow, ("steptwo", "0"))
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=3)

    # steptwo/* depend on joinone/0; mark it failed.
    large_flow.set("record", "status", NodeStatus.ERROR, step="joinone", index="0")

    _launch(scheduler)
    info = scheduler._TaskScheduler__nodes[("steptwo", "0")]
    assert info["proc"] is None
    assert ("steptwo", "0") not in scheduler.get_running_nodes()
    assert ("steptwo", "0") not in scheduler.get_nodes_waiting_to_run()


@pytest.mark.timeout(180)
def test_run_end_to_end_with_breakpoint(large_flow, make_tasks):
    '''A full real run with a breakpoint on a middle node still completes all
    nodes successfully.'''
    _set_breakpoints(large_flow, ("steptwo", "1"))
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    scheduler.run(logging.NullHandler())

    for step, index in large_flow.get("flowgraph", "testflow", field="schema").get_nodes():
        assert large_flow.get("record", "status", step=step, index=index) == NodeStatus.SUCCESS


@pytest.mark.timeout(180)
def test_run_end_to_end_with_multiple_breakpoints(large_flow, make_tasks):
    '''A full real run with breakpoints on several nodes across different
    levels completes all nodes successfully.'''
    _set_breakpoints(large_flow,
                     ("stepone", "0"), ("steptwo", "2"), ("stepthree", "1"))
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    scheduler.run(logging.NullHandler())

    for step, index in large_flow.get("flowgraph", "testflow", field="schema").get_nodes():
        assert large_flow.get("record", "status", step=step, index=index) == NodeStatus.SUCCESS


@pytest.mark.timeout(180)
def test_run_end_to_end_single_parallel_under_breakpoint(large_flow, make_tasks,
                                                         monkeypatch):
    '''End-to-end with a breakpoint on every entry node and only a single core
    available: the run must still complete every node successfully (exercises
    the drain-then-isolate path repeatedly under tight resources).'''
    def one_core(*args, **kwargs):
        return 1
    monkeypatch.setattr(imported_utils, "get_cores", one_core)

    _set_breakpoints(large_flow,
                     ("stepone", "0"), ("stepone", "1"), ("stepone", "2"))
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    scheduler.run(logging.NullHandler())

    for step, index in large_flow.get("flowgraph", "testflow", field="schema").get_nodes():
        assert large_flow.get("record", "status", step=step, index=index) == NodeStatus.SUCCESS
