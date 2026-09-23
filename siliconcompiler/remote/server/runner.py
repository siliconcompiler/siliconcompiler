'''
The process the batch job starts.

``python3 -m siliconcompiler.remote.server.runner <manifest>``

This is the whole of what runs on a compute node. It holds no database
connection and makes no HTTP request: it loads the manifest the server
normalized, runs it, and writes what it is doing into the job's own directory.
The API process reads that file.

🔴 **That indirection is the point.** A run that reported over HTTP would need a
credential on every compute node, and one that wrote to the store would make the
store a thing every node mounts. A file on the filesystem the run already writes
its outputs to costs neither -- and it is why nothing in the job model assumes
the API process is a Slurm submit host.
'''

import argparse
import sys
import traceback

from pathlib import Path

from siliconcompiler.remote.server.runspec import (
    PROGRESS_FILENAME, node_image, node_state, runtime_nodes, write_progress)
from siliconcompiler.remote.server.store import now
from siliconcompiler.utils.logging import SCSuppressLoggerFilter

__all__ = ["main"]


# Module state rather than a closure, because the callbacks are handed to the
# scheduler through a settings object shared with forked children. A plain
# function with no captured frame is the one shape that survives that trip
# unchanged.
_progress_path = None
_progress = None


def _publish() -> None:
    if _progress_path is not None:
        write_progress(_progress_path, _progress)


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
    node["exit_code"] = exit_code
    _publish()


def run(manifest: Path) -> int:
    '''Run one job, reporting as it goes.'''
    global _progress_path, _progress

    from siliconcompiler import Project
    from siliconcompiler.scheduler.taskscheduler import TaskScheduler

    project = Project.from_manifest(filepath=str(manifest))
    _silence_console(project)

    # Beside the manifest, which is the job's own directory. The server put the
    # manifest there and knows where to look without being told a second path.
    _progress_path = Path(manifest).parent / PROGRESS_FILENAME

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

    TaskScheduler.register_callback("pre_node", _node_started)
    TaskScheduler.register_callback("post_node", _node_finished)
    # 🔴 Settled HERE rather than after project.run() returns, because
    # Project.run() resets every non-global parameter on its way out --
    # `record,status` included. Read afterwards it is empty, and every node no
    # callback fired for looks like one the run never reached.
    # 🔴 Registered on BOTH ends of the run. SiliconCompiler decides which
    # nodes it will not execute during setup, before the first one starts, so
    # settling only at the end left a node the run had already written off
    # reading `pending` for the whole run -- and the client showed it as
    # pending right up until the job finished.
    TaskScheduler.register_callback("pre_run", _before_the_flow)
    TaskScheduler.register_callback("post_run", _settle)

    try:
        project.run()
    except Exception as e:
        # The run failing is an outcome this reports, not an error in reporting.
        # What must not happen is the process ending with the progress file
        # still saying `running`, which is indistinguishable from a node that
        # went away -- so the terminal write happens on every path.
        _progress["state"] = "failed"
        _progress["error"] = str(e)
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


def _sweep() -> None:
    for node in _progress["nodes"].values():
        if node["state"] in ("pending", "queued", "preparing", "running"):
            node["state"] = "cancelled"


def _before_the_flow(project) -> None:
    '''The one `pre_run` hook, because there is only one slot for it.

    `TaskScheduler.register_callback` sets a hook rather than appending to it,
    so a second registration replaces the first. Two things have to happen
    before the flow starts and they are sequenced here rather than fighting
    over the slot.
    '''
    _settle(project)
    _fetch_images(project)


def _fetch_images(project) -> None:
    '''Make every container this run needs present, before the flow starts.

    🔴 **This is what `preparing` is for.** A tool image is gigabytes and takes
    minutes on a cold host, and without a state for it the wait is
    indistinguishable from a hang -- a node sitting at `pending` while nothing
    appears to happen is the report a user opens a ticket about.

    Front-loaded rather than fetched at each node's turn, and the reason is the
    scheduler's own shape: `pre_node` fires inside the loop that also reaps
    finished nodes, so a multi-minute pull there would stall the whole flow and
    not just the node waiting for it. Here the pulls are serial -- which is what
    two nodes wanting the same twelve-gigabyte image should do anyway -- and the
    flow starts with everything it needs.

    ⚠️ **A pull that fails is not fatal here.** The node's own launch will try
    again and fail with the message that knows about registry credentials, and
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
        ref = node_image(project, step, index)
        if ref:
            wanted.setdefault(ref, []).append(key)

    if not wanted:
        # Every deployment that runs no containers, which is the default one.
        return

    for ref, keys in sorted(wanted.items()):
        if _image_present(ref):
            continue

        for key in keys:
            _progress["nodes"][key]["state"] = "preparing"
        _publish()

        try:
            _pull_image(ref)
        except Exception as e:                                   # noqa: BLE001
            print(f"could not fetch {ref}: {e}", file=sys.stderr)

        for key in keys:
            # `queued` and not `running`: they are with the scheduler and have
            # not started. Only forwards -- a node that has already begun while
            # a later image was still coming down must not be walked back.
            if _progress["nodes"][key]["state"] == "preparing":
                _progress["nodes"][key]["state"] = "queued"
        _publish()


def _image_present(ref: str) -> bool:
    try:
        import docker

        docker.from_env().images.get(ref)
        return True
    except Exception:                                            # noqa: BLE001
        # No daemon, no image, or no docker package. All three mean *not here*,
        # and the only cost of being wrong is one redundant pull.
        return False


def _pull_image(ref: str) -> None:
    import docker

    docker.from_env().images.pull(ref)


def _silence_console(project) -> None:
    '''Stop this run writing to stdout.

    🔴 The lever the server actually wants, in place of setting `quiet` on
    somebody else's project. `quiet` mutes the console sink and nothing else --
    file sinks ignore it, which is why a quiet run's logs were always complete
    -- so using it here rewrote a caller's setting to achieve something it does
    not do.

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

    ⚠️ Reporting those as `cancelled` read as *the job ended before this node
    started*, which the client then mapped to an error -- so a perfectly
    successful run showed two failures for work nobody ever intended to do.

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
        prog="python3 -m siliconcompiler.remote.server.runner",
        description="Run one job a SiliconCompiler server accepted.")
    parser.add_argument("manifest", help="the normalized manifest to run")

    args = parser.parse_args(argv)
    return run(Path(args.manifest))


if __name__ == "__main__":                                      # pragma: no cover
    sys.exit(main())
