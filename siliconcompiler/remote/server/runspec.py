'''
What a submitted job becomes, in one place.

Two things live here and they are the same decision seen from both ends: the
settings the server applies to an uploaded manifest before anything runs, and the
file the run writes back so the server can say what it is doing. Nothing in this
module imports Flask -- it is read by the API process and by the process the
batch job starts, and those are not the same machine.

🔴 **The settings list is the sanitation policy**, and it survives the code that
holds it. Before this rewrite it was applied in two places with the two copies
disagreeing, which is also why *"two spellings of the same setup are two hashes
of the same job"* is the run hash's precondition.
'''

import json
import os

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["normalize", "node_image", "runtime_flow", "runtime_nodes",
           "node_state", "PROGRESS_FILENAME", "read_progress", "write_progress"]


# Written by the run, read by the API process, and the only channel between
# them. It sits in the job's own directory rather than in the store because the
# two processes share a filesystem and need not share a database -- which is the
# property that lets the scheduler and the API be separated later.
PROGRESS_FILENAME = "sc-server-progress.json"


# SiliconCompiler's runner has its own node vocabulary and it is not the
# contract's. The mapping happens here, at the boundary, which is what keeps the
# published set closed without freezing another project's enum.
_NODE_STATES = {
    "pending": "pending",
    "queued": "queued",
    "running": "running",
    "success": "completed",
    "error": "failed",
    "timeout": "failed",
    "skipped": "skipped",
}


def node_state(status: Optional[str]) -> str:
    '''One SiliconCompiler node status as one of the contract's eight.

    An unmapped status is a mapping bug rather than something to pass through:
    a client switches on this vocabulary, so an unknown value reaching the wire
    would be a state nobody can read. Reported as `failed`, which is the safe
    direction -- terminal, and visible -- rather than leaving a node that will
    never move looking like one that still might.
    '''
    if not status:
        return "pending"
    return _NODE_STATES.get(status, "failed")


def normalize(project, job_id: str, builddir, cachedir, images=None) -> None:
    '''Everything the server decides about how a submitted run executes.

    Applied once, at submit, after the digest has been verified and after the
    archive limits have bound. A client's manifest asserts what to build; every
    setting here is the server's answer to how, and none of them is negotiable:

    - **no dashboard** -- there is no terminal on the server
    - **the build directory** -- ``<datadir>/users/<user>/builds/<job>/``, per
      user as well as per job, so the ownership record is no longer a file
      inside the directory it protects
    - **the cache** -- ``<datadir>/users/<user>/cache/``, per user. Cluster-wide
      would be cheaper by one PDK copy per user and is what this replaced:
      ``ccache`` and ``coursier`` create their own directories, so under a
      shared tree they land with the first user's uid and the second gets
      ``EPERM`` -- and ``chmod`` is owner-only, so nothing can repair a
      directory it did not create
    - 🔴 **remote off** -- the one setting whose absence is an infinite loop.
      Left on, the compute node submits the job again
    - **no display** -- there is none on a compute node

    🔴 **`quiet` is deliberately NOT set, and that is a change.** It used to be,
    on the grounds that *the server's own logging is the record*. It is not what
    `quiet` does: the filter is on the console sink only, and file sinks ignore
    it entirely, so a quiet run's node logs were always complete. What it
    actually did was mute the batch job's stdout -- which is redirected to a
    file nobody tails -- while silently rewriting a setting the submitter owns.
    A manifest that comes back saying `quiet` when the caller never asked for it
    is a manifest that does not describe their run.

    ⚠️ **The thing it was reaching for is real** and is solved where it belongs:
    the runner detaches the project's console handler, so nothing writes to
    stdout on the server. That keeps every node log complete, keeps the server's
    own run log to the run's own messages instead of a concatenation of every
    node's output, and leaves the caller's `quiet` meaning what they set it to.
    - **the remote id** -- the server-owned job id, which is what a user pastes
      back into ``sc-remote``

    🔴 **The per-node SLURM scheduler is deliberately NOT set here, and that is
    a change.** The old server ran the flow in its own process and dispatched
    each node to Slurm, holding a blocking ``srun`` per node for the length of
    the run. The job is now the unit of submission -- one batch job for the
    whole flow, polled once per run -- so the flow inside it runs with the local
    scheduler. That is what makes the API process something other than a Slurm
    submit host, and it is the shape a REST transport can be swapped into.

    ⚠️ **The per-node CONTAINER is a different question and it is set here**,
    for the deployments that answered it. ``images`` maps a node to the
    repository-at-a-digest the server resolved for it, and each one is written
    into ``option,scheduler,queue`` -- which
    :func:`~siliconcompiler.scheduler.docker.get_image` reads ahead of the
    environment and ahead of its own default, so it is the documented place for
    a server to say what a node runs in. Empty on a deployment that runs no
    containers, which is every deployment until an operator says otherwise.
    '''
    project.option.set_nodashboard(True)
    project.option.set_builddir(str(builddir))
    project.option.set_cachedir(str(cachedir))
    project.option.set_remote(False)
    project.option.set_nodisplay(True)
    project.set('record', 'remoteid', job_id)

    for (step, index), ref in (images or {}).items():
        # 🔴 A digest, never a tag. `registry_ref` is what a human typed and it
        # can be rebuilt underneath this job; the digest is what the operator
        # approved. Two runs a month apart silently executing different code is
        # exactly what pinning at registration exists to prevent, and it only
        # prevents it if the pinned form is the one that reaches the node.
        project.option.scheduler.set_name('docker', step=step, index=index)
        project.option.scheduler.set_queue(ref, step=step, index=index)


def node_image(project, step: str, index: str) -> Optional[str]:
    '''The container this node was placed in, or None.

    Read back out of the manifest by the runner, which has no database
    connection and should not need one: the server wrote the answer into the
    same file the run loads.
    '''
    try:
        if project.option.scheduler.get_name(step=step, index=index) != 'docker':
            return None
        return project.option.scheduler.get_queue(step=step, index=index)
    except Exception:                                            # noqa: BLE001
        return None


def runtime_flow(project):
    '''The flow this run will actually execute.

    Not ``project.get_flow()``: ``from``, ``to`` and ``prune`` narrow a
    flowgraph to the part a particular run covers, and a server that wrote a
    row per node of the whole graph would report nodes that were never going to
    run as pending for ever.
    '''
    from siliconcompiler.flowgraph import RuntimeFlowgraph

    return RuntimeFlowgraph(
        project.get_flow(),
        from_steps=project.option.get_from(),
        to_steps=project.option.get_to(),
        prune_nodes=project.option.get_prune())


def runtime_nodes(project) -> List[Tuple[str, str]]:
    '''The nodes this run will execute, in flowgraph order.

    The same derivation on both ends: the server writes a row per node at
    submit, and the run reports against the same list. Deriving it twice from
    the same manifest is what keeps the job object's ``progress`` counts
    matching what actually ran.
    '''
    return list(runtime_flow(project).get_nodes())


######################################################################
# The progress file
######################################################################

def read_progress(path) -> Optional[Dict[str, Any]]:
    '''What the run last said, or None.

    Every failure to read is None rather than an exception: this is read on a
    poll, the writer replaces the file underneath it, and a reader that raised
    would turn a millisecond of rename into a failed request.
    '''
    try:
        with open(path) as f:
            body = json.load(f)
    except (OSError, ValueError):
        return None

    return body if isinstance(body, dict) else None


def write_progress(path, body: Dict[str, Any]) -> None:
    '''Replace the progress file atomically.

    A reader on the other side of a shared filesystem gets the previous
    complete answer or the next one, never half of either.
    '''
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    partial = path.with_name(path.name + ".part")
    with open(partial, "w") as f:
        json.dump(body, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(partial, path)
