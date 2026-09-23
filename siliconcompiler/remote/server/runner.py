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
    PROGRESS_FILENAME, node_state, runtime_nodes, write_progress)
from siliconcompiler.remote.server.store import now

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
        if node["state"] in ("pending", "queued", "running"):
            node["state"] = "cancelled"


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

    `cancelled` is kept for the case it describes: a node with no recorded
    status at all, because the run stopped before reaching it.
    '''
    for key, node in _progress["nodes"].items():
        if node["state"] not in ("pending", "queued", "running"):
            continue

        step, _, index = key.partition("/")
        try:
            recorded = project.get('record', 'status', step=step, index=index)
        except Exception:                                        # noqa: BLE001
            recorded = None

        node["state"] = node_state(recorded) if recorded else "cancelled"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m siliconcompiler.remote.server.runner",
        description="Run one job a SiliconCompiler server accepted.")
    parser.add_argument("manifest", help="the normalized manifest to run")

    args = parser.parse_args(argv)
    return run(Path(args.manifest))


if __name__ == "__main__":                                      # pragma: no cover
    sys.exit(main())
