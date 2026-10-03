'''
The process the batch job starts.

``python3 -m siliconcompiler.remote.server.running.runner <manifest>``

This is the whole of what runs on a compute node. It holds no database
connection and makes no HTTP request: it loads the manifest the job uploaded,
applies the server's overrides to it itself (`runspec.apply_run`), runs it, and
writes what it is doing into the job's own directory. The API process reads
that file.

🔴 **The overrides are applied here, in the job's own SiliconCompiler**, never
by rewriting the manifest in the API process (contract §1): the server writes
what the run needs as data, beside the manifest and outside the tree the upload
expanded into.

🔴 **That indirection is the point.** A run that reported over HTTP would need a
credential on every compute node, and one that wrote to the store would make the
store a thing every node mounts. A file on the filesystem the run already writes
its outputs to costs neither -- and it is why nothing in the job model assumes
the API process is a Slurm submit host.
'''

import argparse
import os
import sys
import threading
import time
import traceback

from pathlib import Path

from siliconcompiler.remote.runflow import runtime_nodes
from siliconcompiler.remote.server.running.runspec import (
    IMAGES_FILENAME, PROGRESS_FILENAME, RUN_FILENAME, apply_run, node_image, node_state,
    read_bundles, read_images, read_run, state_dir, exit_code as published_exit_code,
    write_json)
from siliconcompiler.remote.server.software import images
from siliconcompiler.remote.server.state.store import now
from siliconcompiler.utils.logging import SCSuppressLoggerFilter

__all__ = ["main"]


# Module state rather than a closure, because the callbacks are handed to the
# scheduler through a settings object shared with forked children. A plain
# function with no captured frame is the one shape that survives that trip
# unchanged.
_progress_path = None
_progress = None

# Bundle directory to the reference it unpacks from, and what to mount into
# it, as the server wrote them beside the manifest.
_image_sources = {}
_image_mounts = []
# Each job bundle's shared bundle, and what the job's own bundles mount over it.
_image_shared = {}
_job_mounts = []

# Each placement whose pull failed before the flow started, and what the
# runtime said; and each node the docker daemon reported killed for memory.
_pull_errors = {}
_oom_killed = set()

# Often enough that a stall is noticed in minutes, rarely enough that it is one
# small write a minute on a filesystem every compute node shares. The server's
# patience is its `run_heartbeat_seconds` and is many times this, because a
# missed beat must never be read as a dead run.
HEARTBEAT_SECONDS = 60


def _publish() -> None:
    if _progress_path is not None:
        _progress["heartbeat"] = now()
        write_json(_progress_path, _progress)


def _beat() -> None:
    '''Say *still here* on a timer, for as long as this process lives.

    🔴 **The only other evidence a run exists is the scheduler, and the
    scheduler can be wrong.** A node killed without deleting itself leaves
    Slurm reporting its jobs RUNNING for ever on a machine that is gone -- and
    the API believes the scheduler, so those jobs never leave `running`
    either.

    ⚠️ It cannot be the node transitions `_publish` also writes on. A single
    OpenROAD node runs for half an hour without one, so *nothing written
    lately* and *dead* would be indistinguishable. A timer separates them: the
    file moves every minute whatever the flow is doing, and stops the moment
    this process does.

    A daemon thread, so it never keeps the process alive a moment past the run.
    '''
    while True:
        time.sleep(HEARTBEAT_SECONDS)
        try:
            _publish()
        except Exception:                                        # noqa: BLE001
            # A heartbeat that fails is not a reason to end a run. The server
            # reads staleness, and a run whose filesystem has gone is a run
            # that is about to fail on its own.
            pass


def _key(step: str, index: str) -> str:
    return f"{step}/{index}"


def _node_started(project, step, index) -> None:
    node = _progress["nodes"].setdefault(_key(step, index), {})
    node["state"] = "running"
    node["started_at"] = now()
    _publish()


def _node_finished(project, step, index) -> None:
    status = project.get('record', 'status', step=step, index=index)
    exit_code = project.get('record', 'toolexitcode', step=step, index=index)

    node = _progress["nodes"].setdefault(_key(step, index), {})
    node["state"] = node_state(status)
    node["finished_at"] = now()
    node["exit_code"] = published_exit_code(exit_code)
    if status == "timeout":
        # A limit, named, so the job's error can say which.
        node["limit"] = "time"
    if node["state"] == "failed":
        _explain_failure(project, step, index, node)
    _publish()


def _explain_failure(project, step, index, node) -> None:
    '''Say why a failed node failed where the runtime told us, never by its
    exit status -- 137 is any SIGKILL (implementation-notes §10).

    🔴 **An image that would not pull is an interruption, not the node's
    failure**: the placement the node needed is still not here, and the pull
    of it failed with the runtime's own error, before the flow started. A
    node the docker daemon killed for its memory limit is `run-failed` with
    that limit named.
    '''
    placement = node_image(project, step, index)
    if placement and placement in _pull_errors and not _placement_present(placement):
        node["interrupted"] = {"image": placement[1],
                               "error": _pull_errors[placement][:500]}
    elif (step, index) in _oom_killed:
        node["limit"] = "memory"


def run(manifest: Path) -> int:
    '''Run one job, reporting as it goes.'''
    global _progress_path, _progress

    from siliconcompiler import Project
    from siliconcompiler.scheduler.taskscheduler import TaskScheduler

    _leave_the_allocation()

    project = Project.from_manifest(filepath=str(manifest))
    # The server's answer to how this run executes: its build and cache
    # directories, its placement, where each dataroot is supplied.
    run_data = read_run(state_dir(manifest) / RUN_FILENAME)
    if run_data is not None:
        apply_run(project, run_data)
    _silence_console(project)

    # In the job root, above the tree the upload expanded into, where the
    # server looks without being told a second path.
    _progress_path = state_dir(manifest) / PROGRESS_FILENAME
    global _image_sources, _image_mounts, _image_shared, _job_mounts
    _image_sources, _image_mounts = read_images(state_dir(manifest) / IMAGES_FILENAME)
    _image_shared, _job_mounts = read_bundles(state_dir(manifest) / IMAGES_FILENAME)

    _progress = {
        "state": "running",
        "started_at": now(),
        "finished_at": None,
        "nodes": {_key(step, index): {"state": "pending",
                                      "started_at": None,
                                      "finished_at": None,
                                      "exit_code": None}
                  for step, index in runtime_nodes(project)},
    }
    _publish()

    threading.Thread(target=_beat, daemon=True).start()

    TaskScheduler.register_callback("pre_node", _node_started)
    TaskScheduler.register_callback("post_node", _node_finished)
    # 🔴 Settled HERE rather than after project.run() returns, because
    # Project.run() resets every non-global parameter on its way out --
    # `record,status` included. Read afterwards it is empty, and every node no
    # callback fired for looks like one the run never reached.
    # 🔴 Registered on BOTH ends of the run. SiliconCompiler decides which
    # nodes it will not execute during setup, before the first one starts, so
    # settling only at the end would leave a node the run has already written
    # off reading `pending` until the job finishes.
    TaskScheduler.register_callback("pre_run", _before_the_flow)
    TaskScheduler.register_callback("post_run", _settle)

    try:
        _check_task_classes(project)
        # A node's own Python environment was installed while the job staged
        # -- on the host, into an environment of its key, or into a derived
        # image -- so nothing is installed here, where a line that will not
        # install could only fail the run.
        project.run()
    except Exception as e:
        # The run failing is an outcome this reports, not an error in reporting.
        # What must not happen is the process ending with the progress file
        # still saying `running`, which is indistinguishable from a node that
        # went away -- so the terminal write happens on every path.
        _progress["state"] = "failed"
        # 🔴 This string is the ONLY account of the failure a person on the CLI
        # ever sees: the server publishes it as the job's `error.detail`, and
        # `error.title` is frozen prose that is true of every failed run there
        # has ever been. The class only when there is no message -- a bare
        # `RuntimeError` beats a blank line, and in front of a message that
        # already says what happened it is noise.
        _progress["error"] = str(e) or type(e).__name__
        traceback.print_exc()
        return 1
    else:
        _progress["state"] = "completed"
        return 0
    finally:
        _progress["finished_at"] = now()
        # A run that died before post_run fired leaves its pending nodes here,
        # and `cancelled` is the right answer for those: the run stopped before
        # reaching them.
        _sweep()
        _publish()


def _check_task_classes(project) -> None:
    '''🔴 Fail a node whose task class is not installed where it runs, naming
    it (surface D163), rather than let the flow run it as its base class: a
    task's own setup and pre- and post-processing would silently not happen.
    The server refuses such a job at submit; this is the node's own answer,
    for an image that differs from the server.'''
    flow = project.get_flow()
    missing = {}
    for key in _progress["nodes"]:
        step, _, index = key.partition("/")
        try:
            flow.get_task_module(step, index)
        except (ImportError, AttributeError, ValueError):
            missing[key] = flow.get_graph_node(step, index).get_taskmodule()
    if not missing:
        return

    for key in missing:
        _progress["nodes"][key]["state"] = "failed"
        _progress["nodes"][key]["finished_at"] = now()
    _publish()
    raise RuntimeError(
        "; ".join(f"{key} runs {name}, which is not installed here"
                  for key, name in sorted(missing.items()))
        + " -- so it is not run as its base class instead")


def _leave_the_allocation() -> None:
    '''Stop this process's own batch job from swallowing every node.

    🔴 Slurm decides between a STEP and a JOB by whether ``SLURM_JOB_ID`` is
    set. Inside the orchestrator's allocation every ``srun`` becomes a step in
    it, sharing its resources -- and ``--partition`` on a step is accepted and
    then silently ignored, so a node asking for the compute partition would
    quietly run on the one core the orchestrator was given. Measured on the
    rig rather than assumed::

        srun --partition=sc ...        ->  job=5 step=1    (same allocation)
        SLURM_JOB_ID unset, same call  ->  job=6 step=0    (its own job)

    ⚠️ Cleared for the whole process rather than per call, because nodes run in
    forked children and the environment is what they inherit. Nothing here
    needs the allocation: this process coordinates, and every piece of work it
    submits is scheduled on its own terms.
    '''
    for name in ("SLURM_JOB_ID", "SLURM_JOBID", "SLURM_STEP_ID", "SLURM_STEPID"):
        os.environ.pop(name, None)


def _sweep() -> None:
    '''Decide what became of every node still open when the run ended.

    🔴 Two answers, not one. A node that was RUNNING started and did not
    finish, which is `failed`; a node that never started is `cancelled`, whose
    published meaning is *the job ended before this node started*. Calling the
    first one cancelled says something false about the single node somebody
    looks at first -- it is where the work stopped.
    '''
    for node in _progress["nodes"].values():
        if node["state"] == "running":
            node["state"] = "failed"
            node["finished_at"] = node.get("finished_at") or now()
        elif node["state"] in ("pending", "queued", "preparing"):
            node["state"] = "cancelled"


def _before_the_flow(project) -> None:
    '''The one `pre_run` hook, because there is only one slot for it.

    `TaskScheduler.register_callback` sets a hook rather than appending to it,
    so a second registration replaces the first. Two things have to happen
    before the flow starts and they are sequenced here rather than fighting
    over the slot.
    '''
    _hold_the_window(project)
    _settle(project)
    _fetch_images(project)


def _hold_the_window(project) -> None:
    '''🔴 Fail the run where it has grown past the nodes the server admitted
    (surface D225). SiliconCompiler widens ``[option,from]`` to rebuild an
    upstream node whose results cannot supply what depends on it; here that
    would run a node the job never declared, with no image planned for it.'''
    added = sorted(set(runtime_nodes(project)) - {
        tuple(key.split("/", 1)) for key in _progress["nodes"]})
    if added:
        raise RuntimeError(
            f"the results this run reads cannot supply it: SiliconCompiler would "
            f"rebuild {', '.join('/'.join(node) for node in added)}, which this job "
            "does not run")


def _fetch_images(project) -> None:
    '''Make every container this run needs present, before the flow starts.

    🔴 **This is what `preparing` is for.** A tool image is gigabytes and takes
    minutes on a cold host, and without a state for it the wait is
    indistinguishable from a hang -- a node sitting at `pending` while nothing
    appears to happen is the report a user opens a ticket about.

    Front-loaded rather than fetched at each node's turn, and the reason is the
    scheduler's own shape: `pre_node` fires inside the loop that also reaps
    finished nodes, so a multi-minute fetch there would stall the whole flow and
    not just the node waiting for it. Here they are serial -- which is what two
    nodes wanting the same twelve-gigabyte image should do anyway -- and the
    flow starts with everything it needs.

    ⚠️ **A fetch that fails is not fatal here.** The node's own launch tries
    again and fails with the message that knows about registry credentials, and
    a node that fails is already something this reports. Ending the run from
    here would replace that with a worse error.
    '''
    wanted = {}
    for key, node in _progress["nodes"].items():
        # `_settle` has already run, so a node the flow decided to skip is
        # terminal here. Nothing waits for an image it will never use, and
        # walking it back to `preparing` would be a state going backwards.
        if node["state"] not in ("pending", "queued"):
            continue

        step, _, index = key.partition("/")
        placement = node_image(project, step, index)
        if placement:
            wanted.setdefault(placement, []).append(key)

    if not wanted:
        # Every deployment that runs no containers, which is the default one.
        return

    if any(mechanism == "image" for mechanism, _ in wanted):
        _watch_for_oom()

    for placement, keys in sorted(wanted.items()):
        if _placement_present(placement):
            continue

        for key in keys:
            _progress["nodes"][key]["state"] = "preparing"
        _publish()

        try:
            _make_placement(placement)
        except Exception as e:                                   # noqa: BLE001
            # Into the run log, which the job-level `logs` carries.
            _pull_errors[placement] = str(e) or type(e).__name__
            print(f"could not fetch {placement[1]}: {e}", file=sys.stderr)

        for key in keys:
            # `queued` and not `running`: they are with the scheduler and have
            # not started. Only forwards -- a node that has already begun while
            # a later image was still coming down must not be walked back.
            if _progress["nodes"][key]["state"] == "preparing":
                _progress["nodes"][key]["state"] = "queued"
        _publish()


def _watch_for_oom() -> None:
    '''Listen to the docker daemon for this run's containers being killed
    for memory, as they happen.

    ⚠️ SiliconCompiler's docker scheduler starts each node's container with
    ``auto_remove``, so once it exits its state -- ``OOMKilled`` with it -- is
    gone. The daemon's ``oom`` event names the container's labels, and each
    node's carries ``sc_node:<name>:<step>:<index>``: that needs no change to
    the scheduler.
    '''
    def listen():
        try:
            import docker

            for event in docker.from_env().events(decode=True, filters={"event": "oom"}):
                for label in ((event.get("Actor") or {}).get("Attributes") or {}):
                    # `sc_node:<name>:<step>:<index>`, read from the right: a
                    # node name holds no colon, and a design name may.
                    parts = label.rsplit(":", 2)
                    if label.startswith("sc_node:") and len(parts) == 3:
                        _oom_killed.add((parts[1], parts[2]))
        except Exception:                                        # noqa: BLE001
            # No daemon, no docker package: nothing to be told.
            return

    threading.Thread(target=listen, daemon=True).start()


def _placement_present(placement) -> bool:
    mechanism, where = placement

    if mechanism == "container":
        return images.is_staged(where)

    try:
        import docker

        docker.from_env().images.get(where)
        return True
    except Exception:                                            # noqa: BLE001
        # No daemon, no image, or no docker package. All three mean *not here*,
        # and the only cost of being wrong is one redundant pull.
        return False


def _make_placement(placement) -> None:
    mechanism, where = placement

    if mechanism == "container":
        _unpack_bundle(where)
        return

    import docker

    docker.from_env().images.pull(where)


def _unpack_bundle(bundle: str) -> None:
    '''Turn a registry reference into an OCI bundle Slurm can run.

    The unpack itself is in `images.stage_bundle`, shared with the two callers
    on the server side. What is here is the one thing only this process knows:
    a bundle path names a digest and nothing in it says which registry to pull
    from, so the server wrote that down beside the manifest.
    '''
    source = _image_sources.get(bundle)
    if not source:
        raise RuntimeError(f"nothing recorded to unpack into {bundle}")

    # The shared bundle for the digest, and this job's own over it, which is
    # what the node is started with: its mounts are this job's alone.
    common = Path(_image_shared.get(bundle) or bundle)
    images.stage_bundle(common.parent, source, common.name, mounts=_image_mounts)
    if common != Path(bundle):
        images.job_bundle(common, bundle, _job_mounts)


def _silence_console(project) -> None:
    '''Stop this run writing to stdout.

    🔴 Not by setting `quiet`, which is the submitter's: it mutes the console
    sink and nothing else -- file sinks ignore it -- so setting it would
    rewrite a caller's setting to do no more than this does.

    ⚠️ **Suppressed with a filter rather than detached, and that distinction is
    load-bearing.** `TaskScheduler` captures this handler OBJECT at
    construction and hands it to the `QueueListener` that re-emits every child
    node's records, so removing it from the logger silences the parent's own
    lines and not one line of any node's. It is the same reason the CLI
    dashboard suppresses rather than detaches.

    Every node still writes its own log and the job still writes `job.log`,
    because those are file handlers; what stops is the batch job's stdout,
    which is redirected into the server's run log and would otherwise hold a
    second copy of every line every node produced.
    '''
    console = getattr(project, "_logger_console", None)
    if console is None:
        return

    for existing in console.filters:
        if isinstance(existing, SCSuppressLoggerFilter):
            existing.active = True
            return

    suppress = SCSuppressLoggerFilter()
    suppress.active = True
    console.addFilter(suppress)


def _settle(project) -> None:
    '''Decide what became of every node no callback fired for.

    Runs as the `post_run` hook, while the record still exists.

    🔴 Ask the run what it recorded before assuming the worst. A node the
    scheduler decided not to execute -- metal fill on a PDK that disables it,
    post-route timing repair that is switched off -- is never launched, so
    neither `pre_node` nor `post_node` ever fires for it and it is still
    `pending` here. It was not cancelled: the run considered it and skipped it,
    and `record,status` says so.

    ⚠️ Reporting those as `cancelled` would read as *the job ended before this
    node started*, which a client maps to an error -- so a successful run
    would show failures for work nobody intended to do.

    Nothing is written off here: a node the record says nothing about is left
    as it is, because this runs before the flow starts as well as after it
    ends. `_sweep` is what decides that a node the run never reached is
    `cancelled`, and it only runs once the run is over.
    '''
    changed = False

    for key, node in _progress["nodes"].items():
        if node["state"] not in ("pending", "queued", "running"):
            continue

        step, _, index = key.partition("/")
        try:
            recorded = project.get('record', 'status', step=step, index=index)
        except Exception:                                        # noqa: BLE001
            continue

        if not recorded:
            continue

        mapped = node_state(recorded)
        if mapped != node["state"]:
            node["state"] = mapped
            changed = True

    if changed:
        # Published straight away: settling at the start of a run is only
        # useful if somebody can see it before the run ends.
        _publish()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m siliconcompiler.remote.server.running.runner",
        description="Run one job a SiliconCompiler server accepted.")
    parser.add_argument("manifest", help="the job's manifest, as it was uploaded")

    args = parser.parse_args(argv)
    return run(Path(args.manifest))


if __name__ == "__main__":                                      # pragma: no cover
    sys.exit(main())
