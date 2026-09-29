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
import logging
import os

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("sc-server")

__all__ = ["inheriting_nodes", "normalize", "node_image", "node_tools",
           "runtime_flow", "runtime_nodes",
           "node_state", "exit_code", "PROGRESS_FILENAME", "IMAGES_FILENAME",
           "read_images", "read_python", "write_images", "read_progress",
           "write_progress", "upstream_nodes", "outputs_present"]


# Written by the run, read by the API process, and the only channel between
# them. It sits in the job's own directory rather than in the store because the
# two processes share a filesystem and need not share a database -- which is the
# property that lets the scheduler and the API be separated later.
PROGRESS_FILENAME = "sc-server-progress.json"

# Written by the API process, read by the run, and it answers exactly one
# question: where do the bytes for this container come from.
#
# 🔴 It is not a second copy of the placement. The manifest already says which
# node runs in what, because that is what SiliconCompiler's scheduler executes
# with -- but a bundle path names a directory that may not exist yet, and
# nothing in that path says which registry reference to unpack into it. Two
# consumers, two different facts.
IMAGES_FILENAME = "sc-server-images.json"

# Every `option,scheduler` key: placement is the deployment's, so each is reset
# before the server writes its own.
SCHEDULER_KEYS = ("cores", "defer", "maxnodes", "maxthreads", "memory",
                  "msgcontact", "msgevent", "name", "options", "queue")

# What `normalize` overrides whatever the manifest says -- never refuses.
OVERRIDDEN = frozenset({
    ("option", "nodashboard"), ("option", "builddir"), ("option", "cachedir"),
    ("option", "remote"), ("option", "nodisplay"), ("option", "jobincr"),
    ("record", "remoteid"),
    *(("option", "scheduler", key) for key in SCHEDULER_KEYS),
})


def state_dir(manifest) -> Path:
    '''Where the server's own files for a run live: the job root, above the
    `<design>/<jobname>/` an upload expands into, so no upload can write them.
    The run's manifest is `<job root>/<design>/<jobname>/<design>.pkg.json`.'''
    return Path(os.path.abspath(manifest)).parents[2]


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


def exit_code(value) -> Optional[int]:
    '''A node's exit code as published: 0-255, a signal N as 128+N -- a
    Python return code of -N included -- and None where the tool never exited.'''
    if value is None or isinstance(value, bool):
        return None
    try:
        code = int(value)
    except (TypeError, ValueError):
        return None
    if code < 0:
        code = 128 - code
    return code & 0xFF


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


def normalize(project, job_id: str, builddir, cachedir, images=None,
              cluster: str = "local") -> None:
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

    🔴 **On a cluster every node is its own Slurm job, and that is set here.**
    The API process still submits exactly one thing and polls one id -- the
    run's orchestrator -- so it is not a Slurm submit host and the REST
    transport stays a swap. But the orchestrator computes nothing: it drives the
    flow and hands each node to the cluster, which is what a cluster is for.
    Inside one allocation a flow could never use more than the machine it landed
    on, so scaling the cluster would do nothing for a single run, and the
    orchestrator could not be given a partition of its own because the work
    would follow it there.

    ⚠️ **A job and not a step.** ``srun`` inside an allocation makes a step that
    shares it, and ``--partition`` on a step is accepted and then silently
    ignored -- so the runner drops ``SLURM_JOB_ID`` before the flow starts.

    ⚠️ **The per-node CONTAINER rides on that**, for the deployments that run
    them, and 🔴 **how depends on what is scheduling, because the two mechanisms
    are mutually exclusive.** ``option,scheduler,name`` holds ONE value, so a
    node placed by SiliconCompiler's docker scheduler is a node Slurm never
    sees.

    ================  ====================================================
    ``cluster``       how a node's image reaches it
    ================  ====================================================
    ``slurm``         ``srun --container <bundle>`` on the node's own job
    ``local``         SiliconCompiler's docker scheduler, by digest
    ================  ====================================================

    ⚠️ **``option,scheduler,queue`` is only free on the second row**, and that
    is not a style point: for Slurm it is the PARTITION and goes straight to
    ``srun --partition``. Writing an image reference into it on a cluster would
    submit every node to a partition named after a container.
    '''
    project.option.set_nodashboard(True)
    project.option.set_builddir(str(builddir))
    project.option.set_cachedir(str(cachedir))
    project.option.set_remote(False)
    project.option.set_nodisplay(True)
    # The run is this job: incrementing would run it under another name.
    project.option.set_jobincr(False)
    project.set('record', 'remoteid', job_id)
    for key in SCHEDULER_KEYS:
        project.get('option', 'scheduler', key, field=None).reset()

    if cluster == "slurm":
        # 🔴 EVERY node is its own Slurm job, image or no image. The cluster is
        # what should be scheduling the work: inside one allocation a flow can
        # never use more than the machine it landed on, so scaling the cluster
        # would do nothing for a single run -- and the orchestrator could not
        # be given a partition of its own, because the work would follow it
        # there.
        #
        # ⚠️ A job and not a step, and the runner detaches from its own
        # allocation so it becomes one. A step shares the orchestrator's
        # resources and `--partition` on it is accepted and then SILENTLY
        # IGNORED, so per-node placement would look configured and do nothing.
        for step, index in runtime_nodes(project):
            project.option.scheduler.set_name('slurm', step=step, index=index)
            # A node's terminal state is final, and Slurm already keeps it so:
            # a node is an `srun` job, and Slurm requeues only batch jobs. 🔴
            # Never `--no-requeue` here, which is an sbatch option: srun
            # refuses it and exits 255 before the node is submitted.

            where = (images or {}).get((step, index))
            if where:
                project.option.scheduler.add_options(
                    ['--container', str(where)], step=step, index=index)
    else:
        for (step, index), where in (images or {}).items():
            # 🔴 A digest, never a tag. `registry_ref` is what a human typed
            # and it can be rebuilt underneath this job; the digest is what the
            # operator approved. Two runs a month apart silently executing
            # different code is exactly what pinning at registration prevents,
            # and it only prevents it if the pinned form reaches the node.
            project.option.scheduler.set_name('docker', step=step, index=index)
            project.option.scheduler.set_queue(str(where), step=step, index=index)


def node_image(project, step: str, index: str) -> Optional[Tuple[str, str]]:
    '''How this node is placed, as ``(mechanism, where)``, or None.

    Read back out of the manifest by the runner, which has no database
    connection and should not need one: the server wrote the answer into the
    same file the run loads. ``mechanism`` is ``container`` for a Slurm step
    naming an OCI bundle and ``image`` for a digest the docker scheduler pulls,
    and the runner has to make a different thing exist for each.
    '''
    try:
        placed_by = project.option.scheduler.get_name(step=step, index=index)

        if placed_by == 'docker':
            ref = project.option.scheduler.get_queue(step=step, index=index)
            return ("image", ref) if ref else None

        if placed_by == 'slurm':
            options = project.option.scheduler.get_options(step=step, index=index) or []
            if '--container' in options:
                return ("container", options[options.index('--container') + 1])
    except Exception:                                            # noqa: BLE001
        return None

    return None


def point_dataroots(project, entries, collection) -> int:
    '''Point every dataroot at the copy the run will actually read.

    ``entries`` is `owners.account`'s answer. An uploaded dataroot points at
    this job's upload, a supplied one at this server's own copy -- a held
    source, or an operator's private root -- and an installed package is left
    as it is, since it is found by name.

    🔴 **Two things at once.** The manifest the run writes then records, for
    each dataroot, which copy it resolved to -- the upload's or the server's
    (D111) -- which is what a job's page shows. And no dataroot is left naming
    a path on the submitter's machine, so nothing in the run can reach one:
    the server never reads a path a job names (D112).

    ⚠️ An uploaded file is found in the collection by its dataroot's NAME,
    not its path, so pointing the path at the collection changes nothing about
    how it resolves.

    Returns how many dataroots were pointed.
    '''
    from siliconcompiler.remote import owners

    by = {(entry.kind, entry.name, entry.dataroot): entry for entry in entries}
    pointed = 0
    for key in sorted(project.allkeys(include_default=False)):
        if key[0] == "history" or len(key) < 3 or key[-1] != "path" \
                or key[-3] != "dataroot":
            continue
        who, name = owners.owner(project, key)
        kind = owners.DESIGN if who == owners.PROJECT else who
        name = project.name if who == owners.PROJECT else name
        entry = by.get((kind, name, key[-2]))
        if entry is None:
            continue
        if entry.status == owners.SUPPLIED and entry.root:
            target = str(entry.root)
        elif entry.status == owners.UPLOADED:
            target = str(collection)
        else:
            continue
        project.set(*key, target)
        pointed += 1
    return pointed


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


def upstream_nodes(project, skipped=()) -> List[Tuple[str, str]]:
    '''The nodes a run reads and does not run: every node outside the run
    that a node in it takes inputs from (surface D175). A node in ``skipped``
    -- skipped in the job that ran it -- is looked through to its own inputs,
    since it has no results to read.

    🔴 **One derivation for both ends.** The client decides from it what to
    upload or name in `continues_from`, and the server what must be in the
    upload or copied in; two copies of it would be two answers to which
    results a `-from` run needs.
    '''
    runtime = runtime_flow(project)
    flow = project.get_flow()
    pruned = set(project.option.get_prune() or [])
    running = set(runtime.get_nodes())
    skipped = set(skipped)

    found = set()
    seen = set()
    pending = [source for node in running for source in runtime.get_node_inputs(*node)]
    while pending:
        node = tuple(pending.pop())
        if node in running or node in seen or node in pruned:
            continue
        seen.add(node)
        if node in skipped:
            pending.extend(flow.get(*node, "input"))
        else:
            found.add(node)
    return sorted(found)


def outputs_present(node_dir, design: str) -> bool:
    '''Whether a node's results are there: a file under its ``outputs/`` other
    than its own manifest. The same test on both ends.'''
    import os

    outputs = os.path.join(str(node_dir), "outputs")
    manifest = f"{design}.pkg.json"
    for root, _, files in os.walk(outputs):
        for name in files:
            if root == outputs and name == manifest:
                continue
            return True
    return False


def node_tools(flow, nodes) -> Dict[Tuple[str, str], Optional[str]]:
    '''What each node's image must hold, which is what the resolution needs.

    🔴 **Asked of the task and never inferred.** `Task._remote_toolname`
    declares it; every rule that guesses gets a real task wrong. Inferring
    from `exe` says *nothing* for the slang tasks, which have no executable
    and drive `pyslang` in this process -- and an image without pyslang cannot
    run them. Inferring from the tool NAME says *builtin*, which is not a
    thing anybody installs.

    🔴 Per node rather than a set for the whole flow, because submit resolves N
    images and not one: an `import` node needing nothing but Python has no
    business pulling a twelve-gigabyte OpenROAD image, and the only thing that
    can tell them apart is what each node declares.

    ⚠️ **Here rather than in the server, because both ends derive it.** The
    server needs it to place nodes; the client needs it to say what its flow
    will reach for, which is what lets the server refuse before the archive
    moves. Two copies of this would be two answers to *which image does this
    node need*.

    ⚠️ Read off a BARE task -- no setup, no project -- so a forty-node flow
    costs forty attribute reads and nothing else.
    '''
    wanted: Dict[Tuple[str, str], Optional[str]] = {}
    for step, index in nodes:
        try:
            wanted[(step, index)] = flow.get_task_module(step, index)() \
                ._remote_toolname
        except Exception:                                       # noqa: BLE001
            # A task that will not load declares nothing, which places the
            # node in the job's own image -- the safe direction, since that is
            # what a node needing nothing gets.
            wanted[(step, index)] = None
    return wanted


def inheriting_nodes(flow, nodes, edges) -> Dict[Tuple[str, str],
                                                 Optional[Tuple[str, str]]]:
    '''Nodes that run wherever their input node ran, and where that is.

    🆕 The execute tasks assemble a command out of the manifest, so there is
    nothing to require an image for -- and the environment that produced the
    inputs is the one most likely to be able to run it. Following the previous
    node costs nothing when it does not.

    ⚠️ The FIRST input, where there is more than one. A task computing a
    command over several inputs has no better claim on one of them, and
    picking deterministically beats picking arbitrarily.
    '''
    before: Dict[Tuple[str, str], Tuple[str, str]] = {}
    for from_step, from_index, to_step, to_index in edges:
        before.setdefault((to_step, to_index), (from_step, from_index))

    found: Dict[Tuple[str, str], Optional[Tuple[str, str]]] = {}
    for step, index in nodes:
        try:
            if flow.get_task_module(step, index)()._remote_inherits_env:
                found[(step, index)] = before.get((step, index))
        except Exception:                                       # noqa: BLE001
            continue
    return found


######################################################################
# The progress file
######################################################################

def read_images(path) -> Tuple[Dict[str, str], List[str]]:
    '''What the run needs to make a bundle exist: where from, and what to
    mount into it.'''
    try:
        with open(path) as f:
            body = json.load(f)
    except (OSError, ValueError):
        return {}, []

    if not isinstance(body, dict):
        return {}, []

    return body.get("sources") or {}, body.get("mounts") or []


def read_bundles(path) -> Tuple[Dict[str, str], List[Any], List[str]]:
    '''Each job bundle's shared bundle, what the job's own bundles mount,
    and the bind sources they leave out of the shared configuration.'''
    try:
        with open(path) as f:
            body = json.load(f)
    except (OSError, ValueError):
        return {}, [], []

    if not isinstance(body, dict):
        return {}, [], []

    return (body.get("shared") or {}, body.get("job_mounts") or [],
            body.get("drop") or [])


def _mount(mount):
    '''A mount as JSON: a path, or ``[path, mode]``.'''
    if isinstance(mount, (tuple, list)):
        return [str(mount[0]), str(mount[1])]
    return str(mount)


def write_images(path, sources: Dict[str, str], mounts, python=(), shared=None,
                 job_mounts=(), drop=()) -> None:
    '''``python`` is what the job's `requires.python` names: a node's
    environment is installed with each pinned to the version already there.

    ``mounts`` are baked into a shared bundle when the run unpacks it;
    ``shared`` maps each job bundle to its shared one, and ``job_mounts`` are
    what the job's own bundles add over it.'''
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"sources": sources, "mounts": [_mount(m) for m in mounts],
                   "python": sorted(python), "shared": dict(shared or {}),
                   "job_mounts": [_mount(m) for m in job_mounts],
                   "drop": [str(m) for m in drop]}, f)


def read_python(path) -> List[str]:
    '''What the job's `requires.python` names, as `write_images` wrote it.'''
    try:
        with open(path) as f:
            body = json.load(f)
    except (OSError, ValueError):
        return []
    names = body.get("python") if isinstance(body, dict) else None
    return [name for name in names or [] if isinstance(name, str)]


def read_progress(path, root=None) -> Optional[Dict[str, Any]]:
    '''What the run last said, or None.

    Every failure to read is None rather than an exception: this is read on a
    poll, the writer replaces the file underneath it, and a reader that raised
    would turn a millisecond of rename into a failed request.
    '''
    try:
        # 🔴 The run writes this file, inside the job's tree: given the job's
        # ``root``, a link planted in its place is refused, not followed.
        if root is not None:
            from siliconcompiler.remote.server import confine
            opened = confine.open_inside(root, path, "r")
        else:
            opened = open(path)
        with opened as f:
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
