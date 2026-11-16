'''
The process the batch job starts, and all that runs on a compute node.

``python3 -m siliconcompiler.remote.server.running.runner <manifest>``

It holds no database connection and makes no HTTP request: it applies the
server's overrides, runs the job, and writes its progress into the job's
directory for the API process to read.
'''

import argparse
import sys
import time
import traceback

from pathlib import Path

from siliconcompiler import Project
from siliconcompiler.remote.runflow import runtime_nodes
from siliconcompiler.remote.server.running.runspec import (
    PROGRESS_FILENAME, RUN_FILENAME, apply_run, exit_code, node_state, read_json,
    state_dir, write_json)
from siliconcompiler.scheduler.listener import RunListener

__all__ = ["main"]


# Module state, not the listener's: the scheduler hands the listener on as a copy.
_path = None
_progress = None


def _publish() -> None:
    write_json(_path, _progress)


def _key(step: str, index: str) -> str:
    return f"{step}/{index}"


def _node_started(step, index) -> None:
    node = _progress["nodes"][_key(step, index)]
    node["state"] = "running"
    node["started_at"] = time.time()
    _publish()


def _node_finished(project, step, index) -> None:
    node = _progress["nodes"][_key(step, index)]
    node["state"] = node_state(project.get('record', 'status', step=step, index=index))
    node["finished_at"] = time.time()
    node["exit_code"] = exit_code(
        project.get('record', 'toolexitcode', step=step, index=index))
    _publish()


def _settle(project) -> None:
    '''Take `record,status` for every node no event was reported for: SiliconCompiler
    skips some (metal fill a PDK disables) without a word.'''
    for key, node in _progress["nodes"].items():
        if node["state"] not in ("pending", "queued", "running"):
            continue

        step, _, index = key.partition("/")
        recorded = project.get('record', 'status', step=step, index=index)
        if recorded:
            node["state"] = node_state(recorded)
    _publish()


class _Listener(RunListener):
    '''Settled when the flow starts and when it finishes, not after
    project.run(), which resets `record,status` on its way out.'''

    def flow_started(self, project) -> None:
        _settle(project)

    def node_started(self, project, step, index) -> None:
        _node_started(step, index)

    def node_finished(self, project, step, index) -> None:
        _node_finished(project, step, index)

    def flow_finished(self, project, error) -> None:
        _settle(project)


def run(manifest: Path) -> int:
    '''Run one job, reporting as it goes.'''
    global _path, _progress

    from siliconcompiler.scheduler import Scheduler

    _path = state_dir(manifest) / PROGRESS_FILENAME
    _progress = {"state": "failed", "started_at": time.time(), "finished_at": None,
                 "nodes": {}}

    try:
        project = Project.from_manifest(filepath=str(manifest))
        # Required: a run without the server's settings would use the submitter's.
        settings = read_json(state_dir(manifest) / RUN_FILENAME)
        if settings is None:
            raise RuntimeError("the server's run file is missing")
        apply_run(project, settings)

        _progress["nodes"] = {_key(step, index): {"state": "pending", "started_at": None,
                                                  "finished_at": None, "exit_code": None}
                              for step, index in runtime_nodes(project)}
        _progress["state"] = "running"
        _publish()

        Scheduler.add_listener(_Listener())
        project.run()
    except Exception as e:                                       # noqa: BLE001
        _progress["state"] = "failed"
        # The job's `error.detail`: the class name only when there is no message.
        _progress["error"] = str(e) or type(e).__name__
        traceback.print_exc()
        return 1
    else:
        _progress["state"] = "completed"
        return 0
    finally:
        _progress["finished_at"] = time.time()
        # A node still open when the run ended: running failed, the rest never ran.
        for node in _progress["nodes"].values():
            if node["state"] == "running":
                node["state"] = "failed"
            elif node["state"] in ("pending", "queued"):
                node["state"] = "cancelled"
        _publish()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m siliconcompiler.remote.server.running.runner",
        description="Run one job a SiliconCompiler server accepted.")
    parser.add_argument("manifest", help="the job's manifest, as it was uploaded")

    return run(Path(parser.parse_args(argv).manifest))


if __name__ == "__main__":                                      # pragma: no cover
    sys.exit(main())
