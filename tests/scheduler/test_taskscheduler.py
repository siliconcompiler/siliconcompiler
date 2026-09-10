import logging
import multiprocessing
import os
import sys
import time
import weakref

import pytest

from threading import Lock, Thread
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


def _flood_log_queue(queue):
    '''Writes log records the way a node does, then stays alive.

    Real LogRecords rather than raw bytes: the parent's QueueListener handles
    whatever it reads, and bytes kill its monitor thread instead of exercising
    the path under test.

    It then sleeps rather than returning, because the node has to still be
    running when the interrupt arrives -- the listener drains the queue while the
    run is in progress, so a process that only writes finishes and exits early,
    leaving nothing for the cleanup to halt. The sleep is bounded so a failing
    test cannot leave this behind indefinitely.
    '''
    record = logging.LogRecord("node", logging.INFO, __file__, 0,
                               "x" * 5000, None, None)
    for _ in range(200):
        queue.put(record)
    time.sleep(120)


@pytest.mark.timeout(60)
def test_run_control_c_halts_node_blocked_on_log_queue(large_flow, make_tasks, monkeypatch):
    '''An interrupt must not leave a node process writing into the log queue.

    run()'s cleanup stops the QueueListener, which is the queue's only reader, so
    a node still alive afterwards blocks as soon as the pipe fills. Node
    processes are not daemons, so the interpreter joins them at exit with no
    timeout and never exits -- which presented as a CI job that ran every test,
    printed its summary and then produced no further output until it was killed.

    The deadlock itself cannot be asserted from inside the test process, since
    reproducing it would hang the test rather than fail it. What is asserted is
    the invariant that prevents it: an interrupted run leaves no node alive.

    Only meaningful for the pipe-backed queue the fork path uses; spawn gets a
    manager-backed queue, where there is no such pipe to fill.
    '''
    if get_process_context().get_start_method() != "fork":
        pytest.skip("log queue is only pipe-backed on the fork path")

    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    queue = scheduler._TaskScheduler__log_queue

    filler = get_process_context().Process(target=_flood_log_queue, args=(queue,))

    def dummy_loop():
        filler.start()
        # Let it get far enough to block on a full pipe before interrupting.
        time.sleep(2)
        raise KeyboardInterrupt

    monkeypatch.setattr(scheduler, "_TaskScheduler__run_loop", dummy_loop)
    # Present it the way a launched node appears to the cleanup path.
    scheduler._TaskScheduler__nodes[("filler", "0")] = {"proc": filler}

    try:
        with pytest.raises(SystemExit):
            scheduler.run(logging.NullHandler())

        assert not filler.is_alive(), \
            "interrupt left a node process alive and writing to the log queue"
    finally:
        # Never leave the filler behind if the assertion above fails.
        if filler.is_alive():
            filler.kill()
        filler.join(timeout=10)


def test_run_completion_leaves_nodes_untouched(large_flow, make_tasks, monkeypatch):
    '''The interrupt cleanup must not reach into a normally completed run.

    __run_loop() has joined every process by the time run() returns, so the halt
    step has nothing to do; this pins that it does not terminate anything.
    '''
    killed = []

    class FakeProc:
        def is_alive(self):
            return False

        def terminate(self):
            killed.append("terminate")

        def kill(self):
            killed.append("kill")

    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    monkeypatch.setattr(scheduler, "_TaskScheduler__run_loop", lambda: None)
    scheduler._TaskScheduler__nodes[("done", "0")] = {"proc": FakeProc()}

    scheduler.run(logging.NullHandler())

    assert killed == [], f"completed run must not signal its nodes, got {killed}"


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


def test_process_completed_nodes_merges_paths(large_flow, make_tasks):
    '''A node resolves data sources in its own process, so the paths it found
    must be merged back into the parent.'''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    node = ("stepone", "0")
    _, pipe = _setup_completed_node(scheduler, node, exitcode=0, pipe_has_data=True)
    pipe.recv.return_value = {
        "paths": {"someid": "/some/path"},
        "failures": {"otherid": [3, "FileNotFoundError: simulated 404"]}
    }

    scheduler._TaskScheduler__process_completed_nodes()

    assert MPManager.get_path_cache().get("someid") == "/some/path"


def test_process_completed_nodes_ignores_failures(large_flow, make_tasks):
    '''A fetch that failed for one node may still succeed for the next, so each
    node keeps its own retry budget for now.'''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    node = ("stepone", "0")
    _, pipe = _setup_completed_node(scheduler, node, exitcode=0, pipe_has_data=True)
    pipe.recv.return_value = {
        "paths": {},
        "failures": {"otherid": [3, "FileNotFoundError: simulated 404"]},
        "permanent": ["otherid"]
    }

    scheduler._TaskScheduler__process_completed_nodes()

    assert MPManager.get_path_cache().attempts("otherid") == 0
    assert not MPManager.get_path_cache().is_permanent("otherid")
    assert not MPManager.get_path_cache().is_exhausted("otherid")


def test_process_completed_nodes_tolerates_bad_payload(large_flow, make_tasks):
    '''A garbled or truncated message must not take down the scheduler.'''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    node = ("stepone", "0")
    large_flow.set("record", "status", NodeStatus.SUCCESS, step=node[0], index=node[1])
    _, pipe = _setup_completed_node(scheduler, node, exitcode=0, pipe_has_data=True)
    pipe.recv.return_value = "not a payload"

    scheduler._TaskScheduler__process_completed_nodes()

    assert large_flow.get("record", "status", step=node[0], index=node[1]) == NodeStatus.SUCCESS


def test_process_completed_nodes_tolerates_recv_error(large_flow, make_tasks):
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    node = ("stepone", "0")
    large_flow.set("record", "status", NodeStatus.SUCCESS, step=node[0], index=node[1])
    _, pipe = _setup_completed_node(scheduler, node, exitcode=0, pipe_has_data=True)
    pipe.recv.side_effect = EOFError("pipe is gone")

    scheduler._TaskScheduler__process_completed_nodes()

    assert large_flow.get("record", "status", step=node[0], index=node[1]) == NodeStatus.SUCCESS


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


def test_check_reports_a_dead_branch_a_completed_run_ran_over(project_logger, large_flow,
                                                              make_tasks, caplog):
    """[option,continue] lets the flow reach its exit nodes over a failed node.
    That must not read as a run where nothing failed."""
    project_logger(large_flow)
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    large_flow.set("record", "status", NodeStatus.SUCCESS, step="jointhree", index="0")
    large_flow.set("record", "status", NodeStatus.ERROR, step="stepone", index="0")

    scheduler.check()

    assert "Run completed with errors in: stepone/0" in caplog.text


def test_check_says_nothing_when_nothing_failed(project_logger, large_flow, make_tasks, caplog):
    project_logger(large_flow)
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    large_flow.set("record", "status", NodeStatus.SUCCESS, step="jointhree", index="0")

    scheduler.check()

    assert "Run completed with errors" not in caplog.text


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


# ---------------------------------------------------------------------------
# The launch gate and [option,continue]
#
# A failed dependency normally disqualifies a node before it ever starts. The
# option excuses that failure -- read from the node it happened on, never from
# the node that consumes it -- so the consumer launches and runs on whatever
# else arrived.
#
# Nodes here are built directly rather than through Scheduler, so none of them
# carries the builtin flag and every one exercises the non-builtin path.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("error", [NodeStatus.ERROR, NodeStatus.TIMEOUT])
def test_failed_dep_prunes_a_node(large_flow, make_tasks, error):
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=3)

    large_flow.set("record", "status", error, step="joinone", index="0")

    _launch(scheduler)
    for index in ("0", "1", "2"):
        assert scheduler._TaskScheduler__nodes[("steptwo", index)]["proc"] is None


@pytest.mark.parametrize("error", [NodeStatus.ERROR, NodeStatus.TIMEOUT])
def test_an_excused_failed_dep_still_launches_a_node(large_flow, make_tasks, error):
    # Settle the first level before building the scheduler, so the parallel
    # slots belong to steptwo/* rather than to the entry nodes.
    for index in ("0", "1", "2"):
        large_flow.set("record", "status", NodeStatus.SUCCESS, step="stepone", index=index)
    large_flow.set("record", "status", error, step="joinone", index="0")
    large_flow.option.set_continue(True, step="joinone")

    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=3)

    _launch(scheduler)
    for index in ("0", "1", "2"):
        assert ("steptwo", index) in scheduler.get_running_nodes()


def test_continue_on_the_consumer_does_not_excuse_its_dep(large_flow, make_tasks):
    """The excuse belongs to the node that failed. Annotating the consumer is a
    plausible reading of the option and must not work."""
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=3)

    large_flow.set("record", "status", NodeStatus.ERROR, step="joinone", index="0")
    large_flow.option.set_continue(True, step="steptwo")

    _launch(scheduler)
    for index in ("0", "1", "2"):
        assert scheduler._TaskScheduler__nodes[("steptwo", index)]["proc"] is None


@pytest.mark.parametrize("error", [NodeStatus.ERROR, NodeStatus.TIMEOUT])
def test_a_builtin_with_every_dep_excused_still_launches(large_flow, make_tasks, error):
    """A builtin is normally pruned when nothing upstream succeeded. Excusing
    those failures has to lift that too, or the builtin is left PENDING and its
    own consumers wait on a node that will never reach a terminal state -- the
    thing the excuse exists to avoid. It launches, finds its fan-in empty and
    halts on "No inputs selected"."""
    for index in ("0", "1", "2"):
        large_flow.set("record", "status", error, step="stepone", index=index)
    large_flow.option.set_continue(True, step="stepone")

    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=3)

    _launch(scheduler)
    assert ("joinone", "0") in scheduler.get_running_nodes()


@pytest.mark.parametrize("error", [NodeStatus.ERROR, NodeStatus.TIMEOUT])
def test_a_builtin_with_every_dep_failed_and_unexcused_is_still_pruned(
        large_flow, make_tasks, error):
    """Without the option the builtins behave exactly as they do today."""
    for index in ("0", "1", "2"):
        large_flow.set("record", "status", error, step="stepone", index=index)

    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=3)

    _launch(scheduler)
    assert scheduler._TaskScheduler__nodes[("joinone", "0")]["proc"] is None


def test_an_excused_dep_does_not_launch_a_node_early(large_flow, make_tasks):
    """Excusing a failure says nothing about the dependencies still running:
    the node waits for its whole fan-in to reach a terminal state first."""
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    _mock_all_procs(scheduler)
    _set_resources(scheduler, max_parallel=3)

    large_flow.option.set_continue(True, step="stepone")
    large_flow.set("record", "status", NodeStatus.ERROR, step="stepone", index="0")
    large_flow.set("record", "status", NodeStatus.SUCCESS, step="stepone", index="1")
    # stepone/2 is still PENDING.

    _launch(scheduler)
    assert ("joinone", "0") not in scheduler.get_running_nodes()
    assert ("joinone", "0") in scheduler.get_nodes_waiting_to_run()


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


def _sleep_forever():
    # Bounded so a failing test cannot leave this behind indefinitely.
    time.sleep(120)


@pytest.mark.timeout(60)
def test_halt_all_ends_node_processes(large_flow, make_tasks):
    '''halt_all() reaches a run that the caller holds no handle to.

    This is what a server shutting down mid-job has to work with: the run is
    inside a thread, and its node processes are not daemons, so anything still
    alive is joined at interpreter exit -- which is an sc-server that never goes
    away after being told to stop.
    '''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    proc = get_process_context().Process(target=_sleep_forever)
    proc.start()
    # Present it the way a launched node appears to the halt path.
    scheduler._TaskScheduler__nodes[("sleeper", "0")] = {"proc": proc}

    try:
        assert TaskScheduler.halt_all() == 1
        assert not proc.is_alive()
    finally:
        if proc.is_alive():
            proc.kill()
        proc.join(timeout=10)


@pytest.mark.timeout(60)
def test_cancel_stops_the_run_from_scheduling(large_flow, make_tasks):
    '''A canceled run launches nothing further.

    Ending the node processes is only half of a cancel: the loop that started
    them is untouched by that, and left alone it fills the machine straight back
    up with whatever became ready. Cancelling from post_node is the version that
    tells the two halves apart -- the run's first level has just succeeded, so
    there is a whole next level ready to go and nothing left running to stop.
    '''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    def cancel_run(project, step, index):
        scheduler.cancel()

    TaskScheduler.register_callback("post_node", cancel_run)

    scheduler.run(logging.NullHandler())

    assert scheduler.is_canceled()

    # Nothing downstream of the level that was already running was started:
    # 'stepone' is excluded because those are the nodes the cancel landed among,
    # and which of them completed before it arrived is a race.
    flow = large_flow.get("flowgraph", "testflow", field="schema")
    for step, index in flow.get_nodes():
        if step == "stepone":
            continue
        assert large_flow.get("record", "status", step=step, index=index) == \
            NodeStatus.PENDING, f"{step}/{index} was launched after the cancel"


@pytest.mark.timeout(60)
def test_cancel_ends_running_nodes(large_flow, make_tasks):
    '''Cancelling ends what is running, not just what has yet to start'''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    proc = get_process_context().Process(target=_sleep_forever)
    proc.start()
    # Present it the way a launched node appears to the cancel path.
    scheduler._TaskScheduler__nodes[("sleeper", "0")] = {"proc": proc}

    try:
        assert scheduler.cancel() is True
        assert not proc.is_alive()
        assert scheduler.is_canceled()
    finally:
        if proc.is_alive():
            proc.kill()
        proc.join(timeout=10)


def test_cancel_with_nothing_running(large_flow, make_tasks):
    '''A run with no live nodes is still canceled, it just has none to end'''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    assert scheduler.cancel() is False
    assert scheduler.is_canceled()


@pytest.mark.timeout(60)
def test_canceled_scheduler_runs_nothing(large_flow, make_tasks):
    '''A run canceled before its loop starts launches nothing at all.

    This is what a cancel landing during setup becomes: Scheduler holds the
    request until it has a TaskScheduler to give it to, which is after every
    node is configured but before any has run.
    '''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    scheduler.cancel()

    scheduler.run(logging.NullHandler())

    flow = large_flow.get("flowgraph", "testflow", field="schema")
    for step, index in flow.get_nodes():
        assert large_flow.get("record", "status", step=step, index=index) == \
            NodeStatus.PENDING, f"{step}/{index} ran despite the cancel"


def test_halt_asks_each_node_to_cancel_first(large_flow, make_tasks):
    '''A node dispatched elsewhere is not holding its work in the process about
       to be killed, and killing that process is what puts it out of reach'''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    order = []

    class Node:
        def cancel(self):
            order.append("node")

    class Proc:
        def __init__(self):
            self.__alive = True

        def is_alive(self):
            return self.__alive

        def terminate(self):
            order.append("terminate")
            self.__alive = False

        def kill(self):
            pass

        def join(self, timeout=None):
            pass

    scheduler._TaskScheduler__nodes[("elsewhere", "0")] = {
        "name": "elsewhere/0", "node": Node(), "proc": Proc()}

    assert scheduler.cancel() is True
    assert order == ["node", "terminate"]


def test_halt_ends_nodes_even_when_a_cancel_fails(large_flow, make_tasks, project_logger,
                                                  caplog):
    '''A node's cancel is overridden per scheduler and can shell out. Whatever
       it does wrong, the processes still have to be ended -- leaving them alive
       is the deadlock the halt exists to prevent'''
    project_logger(large_flow)
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    class Node:
        def cancel(self):
            raise RuntimeError("scancel exploded")

    proc = MagicMock()
    proc.is_alive.side_effect = [True, False]

    scheduler._TaskScheduler__nodes[("elsewhere", "0")] = {
        "name": "elsewhere/0", "node": Node(), "proc": proc}

    assert scheduler.cancel() is True
    proc.terminate.assert_called_once()
    assert "Failed to cancel elsewhere/0: scancel exploded" in caplog.text


def test_a_canceled_run_refuses_to_start_a_node(large_flow, make_tasks):
    '''The check that guards a launch, on its own'''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    scheduler.cancel()

    started = []
    scheduler._TaskScheduler__start_node = started.append

    assert scheduler._TaskScheduler__try_start_node(("stepone", "0")) is False
    assert started == []


def test_a_launch_holds_the_cancel_lock(large_flow, make_tasks):
    '''Checking the flag and starting the node have to be one step.

    Apart, a cancel lands between them and its halt scans for live processes
    just before the one it was meant to end exists: nothing stops that node,
    and the run loop goes on to join it -- with a single node running, that
    join has no timeout, so a canceled run sits through a whole task.

    Holding the lock across both is what makes the two orderings the only ones:
    the launch finishes first and halt finds it running, or the cancel gets
    there first and the launch never happens.
    '''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    held = []

    def start_node(node):
        # From another thread: the lock is reentrant, so probing it from this
        # one would succeed whether or not it is held.
        def probe():
            lock = scheduler._TaskScheduler__launch_lock
            acquired = lock.acquire(blocking=False)
            held.append(not acquired)
            if acquired:
                lock.release()

        thread = Thread(target=probe)
        thread.start()
        thread.join(timeout=10)
        assert not thread.is_alive()

    scheduler._TaskScheduler__start_node = start_node
    scheduler._TaskScheduler__allow_start = lambda node: True

    assert scheduler._TaskScheduler__try_start_node(("stepone", "0")) is True
    assert held == [True], "a node was started without the cancel lock held"


def test_check_reports_a_cancel_rather_than_a_broken_flow(large_flow, make_tasks):
    '''A canceled run did not reach its exit nodes, but reporting that as
       unreachable steps sends the reader hunting a failure that never happened'''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    scheduler.cancel()

    with pytest.raises(SCRuntimeError, match="run was canceled before completing"):
        scheduler.check()


def _deaf_node_with_a_tool(marker):
    """A node that ignores the terminate, holding a tool the way a task does.

    Stands in for every way a node fails to clean up after itself: killed
    outright by the SIGKILL fallback, wedged in a call that never returns, or
    on a platform where the signal does not arrive as an interrupt at all. In
    each case the tool is left for the scheduler to find.
    """
    import signal as signal_module
    import subprocess

    signal_module.signal(signal_module.SIGTERM, signal_module.SIG_IGN)
    subprocess.Popen(["sleep", marker])
    time.sleep(120)


def _find_marked(marker):
    """The stand-in tool, if it is running."""
    import psutil

    for proc in psutil.process_iter(["cmdline"]):
        try:
            if marker in (proc.info["cmdline"] or []):
                return proc
        except psutil.Error:
            continue
    return None


@pytest.mark.skipif(sys.platform == "win32", reason="posix process tree")
@pytest.mark.timeout(120)
def test_halt_ends_a_tool_its_node_did_not(large_flow, make_tasks):
    '''Asking a node to clean up cannot be depended on.

    The fallback for a node that will not go is SIGKILL, which no node can
    handle, and by then its tool is reparented with nothing tying it to this
    run. So the scheduler notes what each node started while it can still be
    asked, and ends whatever the node did not take with it.
    '''
    marker = f"{os.getpid()}42"
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    proc = get_process_context().Process(target=_deaf_node_with_a_tool, args=(marker,))
    proc.start()
    scheduler._TaskScheduler__nodes[("deaf", "0")] = {"name": "deaf/0", "proc": proc}

    tool = None
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            tool = _find_marked(marker)
            if tool:
                break
            time.sleep(0.1)
        assert tool is not None, "the stand-in tool never started"

        assert scheduler.cancel() is True

        assert not proc.is_alive(), "a node that ignores SIGTERM was not killed"
        assert _find_marked(marker) is None, \
            "the node was ended but the tool it started was left running"
    finally:
        if proc.is_alive():
            proc.kill()
            proc.join(timeout=10)
        leftover = _find_marked(marker)
        if leftover:
            leftover.kill()


def test_halt_all_with_nothing_running(large_flow, make_tasks):
    '''A run with no live nodes reports nothing to halt'''
    TaskScheduler(large_flow, make_tasks(large_flow))

    assert TaskScheduler.halt_all() == 0


def test_halt_all_forgets_collected_schedulers(large_flow, make_tasks):
    '''The registry holds schedulers weakly, so a finished run is not kept
       alive by being listed in it'''
    import gc

    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))
    ref = weakref.ref(scheduler)

    del scheduler
    gc.collect()

    assert ref() is None
    assert TaskScheduler.halt_all() == 0


class _OverlapProbeProc:
    '''Stands in for a node process, recording halts that overlap.

    The real hazard is two threads in terminate()/join() on one process racing
    on waitpid, which is timing-dependent and does not reproduce on demand. What
    is deterministic, and what the lock is for, is whether two threads are in
    that section at once.
    '''

    def __init__(self, state):
        self.__state = state
        self.__alive = True

    def is_alive(self):
        return self.__alive

    def terminate(self):
        pass

    def kill(self):
        self.__alive = False

    def join(self, timeout=None):
        with self.__state["lock"]:
            self.__state["inside"] += 1
            self.__state["peak"] = max(self.__state["peak"], self.__state["inside"])
        time.sleep(0.05)
        with self.__state["lock"]:
            self.__state["inside"] -= 1
        self.__alive = False


@pytest.mark.timeout(60)
def test_halt_all_is_serialized(large_flow, make_tasks):
    '''Only one thread at a time may be ending a run's node processes.

    run()'s own cleanup and a halt_all() from a server shutting down are exactly
    that pair of callers.
    '''
    scheduler = TaskScheduler(large_flow, make_tasks(large_flow))

    state = {"lock": Lock(), "inside": 0, "peak": 0}
    for num in range(4):
        scheduler._TaskScheduler__nodes[("sleeper", str(num))] = {
            "proc": _OverlapProbeProc(state)
        }

    errors = []

    def halt():
        try:
            TaskScheduler.halt_all()
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [Thread(target=halt) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    # Checked first: a join that timed out returns just like one that finished,
    # so a thread deadlocked on the lock would otherwise leave both assertions
    # below passing -- and a deadlock is what this lock could introduce.
    for thread in threads:
        assert not thread.is_alive(), "a halting thread never came back"

    assert errors == []
    assert state["peak"] == 1, "two threads halted the same run at once"
