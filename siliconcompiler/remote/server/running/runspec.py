'''
What a submitted job becomes: the settings the server applies to an uploaded
manifest, and the files the run and the API process speak through. No Flask:
both the API process and the batch job read it, on different machines.

🔴 The settings list is the sanitation policy, applied in this one place: two
copies would drift, and two spellings of one setup would be two run hashes.
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
           "write_json"]


# Run -> API process, the only channel between them: a shared filesystem, no
# shared database.
PROGRESS_FILENAME = "sc-server-progress.json"

# API process -> run: which registry reference each bundle path unpacks from,
# which the manifest's placement cannot say.
IMAGES_FILENAME = "sc-server-images.json"

# API process -> run: what `apply_run` applies to the uploaded manifest.
RUN_FILENAME = "sc-server-run.json"

# Each uploaded dataroot rebuilt, outside the collection a re-collect moves aside.
UPLOADS_DIRNAME = "sc-server-uploads"

# The manifest read's result (`manifestread`), for a resumed staging and a follow-up.
SUMMARY_FILENAME = "sc-server-summary.json"

# Placement is the deployment's, so every `option,scheduler` key is reset first.
SCHEDULER_KEYS = ("cores", "defer", "maxnodes", "maxthreads", "memory",
                  "msgcontact", "msgevent", "name", "options", "queue")


def state_dir(manifest) -> Path:
    '''The job root, where the server's own files for a run live.

    It is above the `<design>/<jobname>/` an upload expands into, so no upload
    can write them.'''
    return Path(os.path.abspath(manifest)).parents[2]


# SiliconCompiler's node vocabulary to the contract's, mapped at the boundary.
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
    '''A node's exit code as published: 0-255, signal N (or -N) as 128+N, None if none.'''
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

    An unmapped status is `failed`, terminal and visible, never passed through.
    '''
    if not status:
        return "pending"
    return _NODE_STATES.get(status, "failed")


def normalize(project, job_id: str, builddir, cachedir, images=None,
              cluster: str = "local", track: bool = False) -> None:
    '''Everything the server decides about how a submitted run executes.

    Applied by the run itself (:func:`apply_run`). None of it is negotiable:
    no dashboard or display, per-user build and cache directories, the
    server's job id as the remote id, 🔴 remote off (left on, the compute node
    submits the job again), and tracking where ``track``. The cache is per
    user, not shared: ``ccache`` and ``coursier`` dirs would get the first
    user's uid, and ``chmod`` cannot repair them.

    🔴 `quiet` is deliberately not set: it is the submitter's
    (`runner._silence_console` instead). 🔴 On a cluster every node is its own
    Slurm job, so the API process still polls one orchestrator id. 🔴 A node's
    image is ``srun --container`` there and the docker scheduler by digest on
    ``local``: ``option,scheduler,name`` holds one value. ⚠️ For Slurm,
    ``option,scheduler,queue`` is the partition, so never an image reference.
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
        # Off, the job's own setting stands.
        project.option.set_track(True)
    for key in SCHEDULER_KEYS:
        project.get('option', 'scheduler', key, field=None).reset()

    if cluster == "slurm":
        # 🔴 Every node its own Slurm job, image or not: inside one allocation a
        # flow never outgrows its machine. ⚠️ A job, not a step
        # (`runner._leave_the_allocation`).
        for step, index in runtime_nodes(project):
            project.option.scheduler.set_name('slurm', step=step, index=index)
            # 🔴 Never `--no-requeue` here: srun refuses that sbatch option and
            # exits 255, and Slurm requeues only batch jobs anyway.

            where = (images or {}).get((step, index))
            if where:
                project.option.scheduler.add_options(
                    ['--container', str(where)], step=step, index=index)
    else:
        for (step, index), where in (images or {}).items():
            # 🔴 A digest, never a tag: the pinned form has to reach the node
            # (`images.pinned_ref`).
            project.option.scheduler.set_name('docker', step=step, index=index)
            project.option.scheduler.set_queue(str(where), step=step, index=index)


def node_image(project, step: str, index: str) -> Optional[Tuple[str, str]]:
    '''How this node is placed, as ``(mechanism, where)``, or None.

    ``container`` is an OCI bundle for ``srun``, ``image`` a digest the docker
    scheduler pulls.
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


def dataroot_targets(entries, collection, uploads=None) -> List[List[Optional[str]]]:
    '''Where each dataroot the run reads is supplied, from `owners.account_records`.

    A supplied one is ``[keypath, server_copy]``; an uploaded one is
    ``[keypath, target, collection]``, the target a directory under ``uploads``
    (default: the job root's :data:`UPLOADS_DIRNAME`) the run rebuilds.
    Installed packages and files in no dataroot are left out.'''
    import hashlib

    from siliconcompiler.remote import owners

    if uploads is None:
        uploads = Path(collection).parents[2] / UPLOADS_DIRNAME
    found = []
    for entry in entries:
        if not entry.keypath:
            continue
        if entry.status == owners.SUPPLIED and entry.root:
            found.append([list(entry.keypath), str(entry.root)])
        elif entry.status == owners.UPLOADED:
            # By keypath, so two sharing a name stay apart; hashed, as names are free text.
            name = hashlib.sha1(json.dumps(list(entry.keypath)).encode()).hexdigest()[:16]
            found.append([list(entry.keypath), str(Path(uploads) / name), str(collection)])
    return found


def point_dataroots(project, targets) -> int:
    '''Point every dataroot at the copy the run will read; returns how many.

    🔴 The run's manifest then records which copy each resolved to (D111), and
    no dataroot names a path on the submitter's machine (D112). An uploaded
    dataroot is rebuilt first: collected files are filed by a hash of the
    dataroot's source, so repointing it would lose them.
    '''
    uploaded: Dict[Tuple[str, ...], Tuple[str, str]] = {
        tuple(entry[0]): (entry[1], entry[2]) for entry in targets
        if len(entry) > 2 and entry[2]}
    if uploaded:
        _rebuild_uploads(project, uploaded)

    # 🔴 By the dataroot's own keypath, so each task's is pointed on its own.
    by = {tuple(entry[0]): entry[1] for entry in targets}
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


def _rebuild_uploads(project, uploaded: Dict[Tuple[str, ...], Tuple[str, str]]) -> None:
    '''Link or copy each uploaded dataroot's values from the collection to its target.

    Before any dataroot is pointed, which would move where `collect` filed
    them. Both ends are confined, and a value not collected is never
    looked for elsewhere.
    '''
    import shutil

    from siliconcompiler.remote import owners

    def place(src, dst):
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)

    for collection in sorted({where for _, where in uploaded.values()}):
        for record in owners.value_records(project, collection):
            keypath = tuple(record["keypath"] or ())
            if keypath not in uploaded or uploaded[keypath][1] != collection \
                    or not record["collected"]:
                continue
            src = owners.confined(collection, record["collected"])
            dst = owners.confined(uploaded[keypath][0], record["path"])
            if src is None or dst is None or not os.path.exists(src):
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.isdir(src):
                shutil.copytree(src, dst, copy_function=place, dirs_exist_ok=True)
            elif not os.path.exists(dst):
                place(src, dst)


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
    '''Apply the server's overrides in the job's own SiliconCompiler.

    🔴 Here and nowhere else: the API process never rewrites a manifest (contract §1).
    '''
    normalize(project, run["job_id"], run["builddir"], run["cachedir"],
              images={(step, index): where for step, index, where in run["placements"]},
              cluster=run["cluster"], track=run.get("track", False))
    point_dataroots(project, run["dataroots"])


def read_images(path) -> Tuple[Dict[str, str], List[str]]:
    '''Each bundle's source reference, and what to mount into it.'''
    try:
        with open(path) as f:
            body = json.load(f)
    except (OSError, ValueError):
        return {}, []

    if not isinstance(body, dict):
        return {}, []

    return body.get("sources") or {}, body.get("mounts") or []


def read_bundles(path) -> Tuple[Dict[str, str], List[Any]]:
    '''Each job bundle's shared bundle, and what the job's own bundles mount.'''
    try:
        with open(path) as f:
            body = json.load(f)
    except (OSError, ValueError):
        return {}, []

    if not isinstance(body, dict):
        return {}, []

    return body.get("shared") or {}, body.get("job_mounts") or []


def _mount(mount):
    '''A mount as JSON: a path, or ``[path, mode]``.'''
    if isinstance(mount, (tuple, list)):
        return [str(mount[0]), str(mount[1])]
    return str(mount)


def write_images(path, sources: Dict[str, str], mounts, shared=None,
                 job_mounts=()) -> None:
    '''``mounts`` go into a shared bundle; ``job_mounts`` into the job's own over it.'''
    write_json(path, {"sources": sources, "mounts": [_mount(m) for m in mounts],
                      "shared": dict(shared or {}),
                      "job_mounts": [_mount(m) for m in job_mounts]})


def read_progress(path, root=None) -> Optional[Dict[str, Any]]:
    '''What the run last said, or None on any failure to read: it is read on a poll.'''
    try:
        # 🔴 The run writes this file: given ``root``, a planted link is refused.
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
    '''Replace one of the server's own files atomically, for a reader across a shared filesystem.'''
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    partial = path.with_name(path.name + ".part")
    with open(partial, "w") as f:
        json.dump(body, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(partial, path)
