'''
What a submitted job becomes: the settings the server applies to an uploaded
manifest, and the files the run and the API process speak through. No Flask:
both the API process and the batch job read it, possibly on different machines.
'''

import json
import os

from pathlib import Path
from typing import Any, Dict, Optional

from siliconcompiler.remote.runflow import runtime_nodes

__all__ = ["PROGRESS_FILENAME", "RUN_FILENAME", "apply_run", "exit_code", "node_state",
           "read_json", "state_dir", "write_json"]


# Run -> API process: a shared filesystem, no shared database.
PROGRESS_FILENAME = "sc-server-progress.json"

# API process -> run: what `apply_run` applies to the uploaded manifest.
RUN_FILENAME = "sc-server-run.json"

# Placement is the deployment's, so every `option,scheduler` key is reset first.
SCHEDULER_KEYS = ("cores", "defer", "maxnodes", "maxthreads", "memory",
                  "msgcontact", "msgevent", "name", "options", "queue")

# SiliconCompiler's node vocabulary to the API's, mapped at the boundary.
_NODE_STATES = {
    "pending": "pending",
    "queued": "queued",
    "running": "running",
    "success": "completed",
    "error": "failed",
    "timeout": "failed",
    "skipped": "skipped",
}


def state_dir(manifest) -> Path:
    '''The job root, where the server's own files for a run live: above the
    ``<design>/<jobname>/`` an upload expands into, so no upload can write them.'''
    return Path(os.path.abspath(manifest)).parents[2]


def node_state(status: Optional[str]) -> str:
    '''One SiliconCompiler node status as one of the API's eight; an unmapped
    status is `failed`, terminal and visible, never passed through.'''
    return _NODE_STATES.get(status, "failed") if status else "pending"


def exit_code(value) -> Optional[int]:
    '''A node's exit code as published: 0-255, signal N (or -N) as 128+N, None if none.'''
    if value is None or isinstance(value, bool):
        return None
    try:
        code = int(value)
    except (TypeError, ValueError):
        return None
    return (128 - code if code < 0 else code) & 0xFF


def apply_run(project, run: Dict[str, Any]) -> None:
    '''Apply the server's overrides, in the run's own process and nowhere else.

    None of it is negotiable: no dashboard or display, the job's build directory
    and the server's cache, the server's job id as the remote id, and remote off (left on,
    the run would submit the job again). The run is this job, so a name is never
    incremented.
    '''
    project.option.set_nodashboard(True)
    project.option.set_quiet(True)
    project.option.set_nodisplay(True)
    project.option.set_remote(False)
    project.option.set_jobincr(False)
    project.option.set_builddir(run["builddir"])
    project.option.set_cachedir(run["cachedir"])
    project.set('record', 'remoteid', run["job_id"])

    for key in SCHEDULER_KEYS:
        project.get('option', 'scheduler', key, field=None).reset()

    if run["cluster"] == "slurm":
        for step, index in runtime_nodes(project):
            project.option.scheduler.set_name('slurm', step=step, index=index)


def read_json(path) -> Optional[Dict[str, Any]]:
    '''A server file, or None on any failure to read it: progress is read on a poll.'''
    try:
        with open(path) as f:
            body = json.load(f)
    except (OSError, ValueError):
        return None
    return body if isinstance(body, dict) else None


def write_json(path, body: Any) -> None:
    '''Replace one of the server's own files atomically, for a reader across a
    shared filesystem.'''
    path = Path(path)
    partial = path.with_name(path.name + ".part")
    with open(partial, "w") as f:
        json.dump(body, f)
    os.replace(partial, path)
