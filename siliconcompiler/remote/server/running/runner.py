'''
The process the batch job starts, and all that runs on a compute node.

``python3 -m siliconcompiler.remote.server.running.runner <manifest>``

It holds no database connection and makes no HTTP request, so no compute node
needs a credential or the store: it applies the server's overrides in the job's
own SiliconCompiler (`runspec.apply_run`, contract §1), runs the job, and writes
its progress into the job's directory for the API process to read.
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


# Module state, not a closure: the callbacks reach forked children through a
# shared settings object, and only a plain function survives that trip.
_progress_path = None
_progress = None

# Bundle directory -> reference it unpacks from, and what to mount into it.
_image_sources = {}
_image_mounts = []
# Each job bundle's shared bundle, and what the job's own bundles mount over it.
_image_shared = {}
_job_mounts = []

# Placement -> the runtime's pull error; nodes the docker daemon OOM-killed.
_pull_errors = {}
_oom_killed = set()

# The server's `run_heartbeat_seconds` is many times this, so a missed beat is
# never read as a dead run.
HEARTBEAT_SECONDS = 60


def _publish() -> None:
    if _progress_path is not None:
        _progress["heartbeat"] = now()
        write_json(_progress_path, _progress)


def _beat() -> None:
    '''Say *still here* on a timer, for as long as this process lives.

    The scheduler can be wrong: a vanished machine leaves Slurm reporting
    its jobs RUNNING forever. Node transitions cannot stand in for this: one
    OpenROAD node can run half an hour without one.
    '''
    while True:
        time.sleep(HEARTBEAT_SECONDS)
        try:
            _publish()
        except Exception:                                        # noqa: BLE001
            # Never a reason to end a run: the server reads staleness.
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
        node["limit"] = "time"
    if node["state"] == "failed":
        _explain_failure(project, step, index, node)
    _publish()


def _explain_failure(project, step, index, node) -> None:
    '''Say why a failed node failed where the runtime told us, never by exit status.

    137 is any SIGKILL (implementation-notes §10). An image that would not
    pull is an interruption, not the node's failure; an OOM kill names the
    memory limit.
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
    run_data = read_run(state_dir(manifest) / RUN_FILENAME)
    if run_data is not None:
        apply_run(project, run_data)
    _silence_console(project)

    # In the job root, above the tree the upload expanded into.
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
    # Settled in hooks, not after project.run(), which resets `record,status`
    # on its way out; and on both ends, since skipped nodes are decided in setup.
    TaskScheduler.register_callback("pre_run", _before_the_flow)
    TaskScheduler.register_callback("post_run", _settle)

    try:
        _check_task_classes(project)
        # Python packages were installed while staging, never here.
        project.run()
    except Exception as e:
        _progress["state"] = "failed"
        # The job's `error.detail`, the only account of the failure a CLI
        # user sees; the class name only when there is no message.
        _progress["error"] = str(e) or type(e).__name__
        traceback.print_exc()
        return 1
    else:
        _progress["state"] = "completed"
        return 0
    finally:
        _progress["finished_at"] = now()
        # On every path, so the file never ends saying `running`.
        _sweep()
        _publish()


def _check_task_classes(project) -> None:
    '''Fail a node whose task class is not installed here, naming it (surface D163).

    Run as its base class, its own setup and processing would silently not happen.'''
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

    With ``SLURM_JOB_ID`` set, every ``srun`` becomes a step in this
    allocation and its ``--partition`` is silently ignored, so nodes would share
    the orchestrator's one core. Cleared process-wide: forked nodes inherit it.
    '''
    for name in ("SLURM_JOB_ID", "SLURM_JOBID", "SLURM_STEP_ID", "SLURM_STEPID"):
        os.environ.pop(name, None)


def _sweep() -> None:
    '''Decide what became of every node still open when the run ended.

    A running node is `failed`, where the work stopped; one that never
    started is `cancelled`.
    '''
    for node in _progress["nodes"].values():
        if node["state"] == "running":
            node["state"] = "failed"
            node["finished_at"] = node.get("finished_at") or now()
        elif node["state"] in ("pending", "queued", "preparing"):
            node["state"] = "cancelled"


def _before_the_flow(project) -> None:
    '''The one `pre_run` hook: `register_callback` replaces rather than appends.'''
    _hold_the_window(project)
    _settle(project)
    _fetch_images(project)


def _hold_the_window(project) -> None:
    '''Fail the run where it has grown past the nodes the server admitted (surface D225).

    SiliconCompiler may widen ``[option,from]`` to rebuild an upstream node,
    which would run a node with no image planned for it.'''
    added = sorted(set(runtime_nodes(project)) - {
        tuple(key.split("/", 1)) for key in _progress["nodes"]})
    if added:
        raise RuntimeError(
            f"the results this run reads cannot supply it: SiliconCompiler would "
            f"rebuild {', '.join('/'.join(node) for node in added)}, which this job "
            "does not run")


def _fetch_images(project) -> None:
    '''Make every container this run needs present, showing `preparing` meanwhile.

    Front-loaded: in `pre_node` a multi-minute fetch would stall the loop that
    reaps every node. A failed fetch is not fatal here: the node's own
    launch retries and fails with a better message.
    '''
    wanted = {}
    for key, node in _progress["nodes"].items():
        # After `_settle`: a skipped node is terminal and must not go backwards.
        if node["state"] not in ("pending", "queued"):
            continue

        step, _, index = key.partition("/")
        placement = node_image(project, step, index)
        if placement:
            wanted.setdefault(placement, []).append(key)

    if not wanted:
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
            # Only forwards: a node may have begun while a later image came down.
            if _progress["nodes"][key]["state"] == "preparing":
                _progress["nodes"][key]["state"] = "queued"
        _publish()


def _watch_for_oom() -> None:
    '''Listen to the docker daemon for this run's containers being OOM-killed.

    Containers are ``auto_remove``, so ``OOMKilled`` is gone once one exits;
    the ``oom`` event carries the node's ``sc_node:`` label instead.
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
        # Being wrong costs one redundant pull.
        return False


def _make_placement(placement) -> None:
    mechanism, where = placement

    if mechanism == "container":
        _unpack_bundle(where)
        return

    import docker

    docker.from_env().images.pull(where)


def _unpack_bundle(bundle: str) -> None:
    '''Unpack the reference the server recorded for ``bundle`` into an OCI bundle.'''
    source = _image_sources.get(bundle)
    if not source:
        raise RuntimeError(f"nothing recorded to unpack into {bundle}")

    # The shared bundle for the digest, and this job's own over it with its mounts.
    common = Path(_image_shared.get(bundle) or bundle)
    images.stage_bundle(common.parent, source, common.name, mounts=_image_mounts)
    if common != Path(bundle):
        images.job_bundle(common, bundle, _job_mounts)


def _silence_console(project) -> None:
    '''Stop this run writing to stdout, which would copy every node's log into the run log.

    Not by setting `quiet`, which is the submitter's. A filter, not a
    detach: `TaskScheduler` hands this handler object to the `QueueListener`
    that re-emits node records, so detaching silences only the parent.
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
    '''Take `record,status` for every node no callback fired for.

    A node the scheduler skipped (metal fill a PDK disables) never fires a
    callback; calling it `cancelled` would show a client an error for work
    nobody intended. Runs before the flow too, so nothing is written off
    here: that is `_sweep`'s.
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
