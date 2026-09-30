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

from siliconcompiler.remote.runflow import runtime_nodes

logger = logging.getLogger("sc-server")

__all__ = ["normalize", "node_image", "node_state", "exit_code", "PROGRESS_FILENAME",
           "IMAGES_FILENAME", "read_images", "write_images", "read_progress",
           "write_progress"]


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

# Written by the API process, read by the run: what the run needs from the
# server -- the job id, the build and cache directories, each node's
# placement, the cluster, and where each dataroot is supplied. The runner
# applies it to the uploaded manifest in the job's own SiliconCompiler
# (`apply_run`); nothing in the API process rewrites the manifest.
RUN_FILENAME = "sc-server-run.json"

# What the manifest's read returned (`manifestread`), kept for a resumed
# staging and a follow-up's allowed set. Written by the API process; no
# upload can reach it.
SUMMARY_FILENAME = "sc-server-summary.json"

# Every `option,scheduler` key: placement is the deployment's, so each is reset
# before the server writes its own.
SCHEDULER_KEYS = ("cores", "defer", "maxnodes", "maxthreads", "memory",
                  "msgcontact", "msgevent", "name", "options", "queue")


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
              cluster: str = "local", track: bool = False) -> None:
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
    - **tracking**, where ``track`` -- the deployment's ``track_provenance``:
      each node records the machine it ran on. Only ever turned on here

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
    if track:
        # Where each node ran, in its record: the deployment's
        # `track_provenance`. Off, the job's own setting stands.
        project.option.set_track(True)
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


def dataroot_targets(entries, collection) -> List[List[Optional[str]]]:
    '''Where each dataroot the run reads is supplied, from `owners.account`'s
    answer, as ``[keypath, target]``: an uploaded one at this job's
    collection, a supplied one at this server's own copy -- a held source, or
    an operator's private root. An installed package is left out, since it is
    found by name, and so are files in no dataroot.'''
    from siliconcompiler.remote import owners

    found = []
    for entry in entries:
        if not entry.keypath:
            continue
        if entry.status == owners.SUPPLIED and entry.root:
            target = str(entry.root)
        elif entry.status == owners.UPLOADED:
            target = str(collection)
        else:
            continue
        found.append([list(entry.keypath), target])
    return found


def point_dataroots(project, targets) -> int:
    '''Point every dataroot at the copy the run will actually read.

    ``targets`` is :func:`dataroot_targets`' answer.

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
    # 🔴 By the dataroot's own keypath -- the parameter's key less `path` --
    # so each task's dataroot is pointed on its own, never every task of the
    # tool at the first one's copy.
    by = {tuple(keypath): target for keypath, target in targets}
    pointed = 0
    for key in sorted(project.allkeys(include_default=False)):
        if key[0] == "history" or len(key) < 3 or key[-1] != "path" \
                or key[-3] != "dataroot":
            continue
        target = by.get(tuple(key[:-1]))
        if target is None:
            continue
        project.set(*key, target)
        pointed += 1
    return pointed


def write_run(path, job_id: str, builddir, cachedir, cluster: str,
              placements=None, dataroots=(), track: bool = False) -> None:
    '''What the run needs from the server: see `RUN_FILENAME`.'''
    write_json(path, {
        "job_id": job_id, "builddir": str(builddir), "cachedir": str(cachedir),
        "cluster": cluster, "track": bool(track),
        "placements": [[step, index, str(where)]
                       for (step, index), where in sorted((placements or {}).items())],
        "dataroots": [list(entry) for entry in dataroots]})


def read_run(path) -> Optional[Dict[str, Any]]:
    ''':func:`write_run`'s file, or None where there is none.'''
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def apply_run(project, run: Dict[str, Any]) -> None:
    '''The server's overrides, applied to the uploaded manifest by the run
    itself, in the job's own SiliconCompiler: :func:`normalize`, then
    :func:`point_dataroots`.

    🔴 **Here and nowhere else.** The API process never rewrites a manifest
    (contract §1): it writes what the run needs as data, and this is where the
    manifest becomes the one the run executes.
    '''
    normalize(project, run["job_id"], run["builddir"], run["cachedir"],
              images={(step, index): where for step, index, where in run["placements"]},
              cluster=run["cluster"], track=run.get("track", False))
    point_dataroots(project, run["dataroots"])


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


def write_images(path, sources: Dict[str, str], mounts, shared=None,
                 job_mounts=(), drop=()) -> None:
    '''``mounts`` are baked into a shared bundle when the run unpacks it;
    ``shared`` maps each job bundle to its shared one, and ``job_mounts`` are
    what the job's own bundles add over it.'''
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"sources": sources, "mounts": [_mount(m) for m in mounts],
                   "shared": dict(shared or {}),
                   "job_mounts": [_mount(m) for m in job_mounts],
                   "drop": [str(m) for m in drop]}, f)


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
            from siliconcompiler.remote.server.outputs import confine
            opened = confine.open_inside(root, path, "r")
        else:
            opened = open(path)
        with opened as f:
            body = json.load(f)
    except (OSError, ValueError):
        return None

    return body if isinstance(body, dict) else None


def write_json(path, body: Any) -> None:
    '''Replace one of the server's own files atomically.'''
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    with open(partial, "w") as f:
        json.dump(body, f)
    os.replace(partial, path)


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
