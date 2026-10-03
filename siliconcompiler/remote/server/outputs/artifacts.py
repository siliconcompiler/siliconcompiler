'''
What a finished run left behind, as artifact rows.

The results tarball is an artifact, not an endpoint: every object is a row
with a kind and a retention, so the listing answers *where did my results go*
even when the bytes are gone. Every kind is stored and served gzipped (surface
§21):

``manifest``    the job's ``<design>.pkg.json``, job-level. Often the only one
                left, and it carries the record: node states, metrics, versions
``logs``        a node's log files as a gzip tar; plus one job-level, SC's own
                ``job.log`` and nothing of this server's
``staging``     this server's scrubbed record for the submitter, one per job
``diagnostics`` the operators' unscrubbed record, job-level and per node;
                never handed over the API
``node``        one node's whole working directory, indexed as the node
                finishes; always bound to a step and an index
``reports``     a node's ``reports/``, a deliberate second copy: above
                ``limits.max_download_bytes`` the node archive is refused while
                the reports are still served
``input``       each upload, moved in and kept even when the job is refused
                (except `jobs.rows._kept`); and a node's ``inputs/``, as links
                to upstream outputs. Neither is a node-archive member

``outputs`` is deliberately not produced: it would copy the large half.
An ``issue`` at a node's coordinates is not a node-archive member either: it
is never fetchable, so counting it would gate the archive on a file not in it.
'''

import gzip
import logging
import os
import shutil
import sqlite3
import tarfile
import uuid

from pathlib import Path
from typing import Any, Dict, Optional

from siliconcompiler.remote import links
from siliconcompiler.remote.server.outputs import confine, record
from siliconcompiler.remote.server.state.store import now, stamp
from siliconcompiler.utils import file_digest

__all__ = ["collect", "collect_node", "cause", "wire", "fetchable", "KINDS", "log_text",
           "referenced_elsewhere"]


logger = logging.getLogger("sc-server")


# The kinds a surface may hand over. `input` is left out because the owner
# already has its bytes, `diagnostics` because it never goes over the API.
KINDS = ("manifest", "logs", "staging", "reports", "node")


def collect_node(store, storage, config, job, build_root, step, index) -> int:
    '''Index one node's results, the moment that node is done.

    Not deferrable to the end of the job: a terminal node answers `/logs`
    with a `303` to its archived log while the rest of the flow runs on.
    '''
    workdir = Path(build_root) / job["design"] / job["jobname"] / step / index
    if not workdir.is_dir():
        return 0

    location = config["storage_location_id"]
    floor = config.limits["artifact_retention_seconds"]
    written = 0

    # Every read below is confined (see `confine`): a node can leave a link
    # anywhere, and following one would index the host's files as results.
    root = Path(build_root)
    # Where a link may end, walked once for this node's archives (database D142).
    job_tree = root / job["design"] / job["jobname"]
    homes = links.Homes(job_tree)

    written += _log_archive(store, storage, job, location, floor, step, index,
                            workdir, root)

    # The node's own manifest, bound to the node: a deployment that hands
    # over manifests and no bulk output can still show a node's record.
    # A deliberate second copy of a file the node archive holds.
    manifest = workdir / "outputs" / f"{job['design']}.pkg.json"
    written += _index(store, storage, job, location, floor, "manifest",
                      step, index, manifest, root)

    # Before the node archive, so a failure partway leaves the small object
    # a person reads already written.
    reports = workdir / "reports"
    if _real_dir(reports) and any(reports.iterdir()):
        written += _archive(store, storage, job, location, floor, "reports",
                            step, index, reports, workdir, root, job_tree=job_tree,
                            homes=homes)

    # A link inside the job stays a link, pointed at the file's real home,
    # so a node archive is not self-contained: a passed-through file resolves
    # where its home node is unpacked beside it (database D142).
    if any(child.name not in _NOT_IN_A_NODE for child in workdir.iterdir()):
        written += _archive(store, storage, job, location, floor, "node",
                            step, index, workdir, workdir, root, skip=_NOT_IN_A_NODE,
                            job_tree=job_tree, homes=homes)

    # What the node was handed, which the node archive leaves out.
    inputs = workdir / "inputs"
    if _real_dir(inputs) and any(inputs.iterdir()):
        written += _archive(store, storage, job, location, floor, "input",
                            step, index, inputs, workdir, root, job_tree=job_tree,
                            homes=homes)

    return written


def record_upload(store, storage, config, job, upload: Path, digest: str,
                  size: int) -> str:
    '''Keep one upload as a job-level `input`, numbered by `upload_seq`; returns its id.

    Moved, not copied: the upload was going to be deleted anyway.
    '''
    artifact_id = str(uuid.uuid4())
    target = storage.artifact_dir(job["id"]) / artifact_id
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(upload, target)

    store.execute(
        'INSERT INTO artifacts (id, job_id, step, "index", digest, '
        "  location_id, storage_key, size_bytes, media_type, kind, upload_seq, "
        "  retained_until, provenance) "
        "VALUES (?, ?, NULL, NULL, ?, ?, ?, ?, 'application/gzip', 'input', "
        "  (SELECT coalesce(max(upload_seq), 0) + 1 FROM artifacts WHERE job_id = ?), "
        "  ?, 'declared')",
        (artifact_id, job["id"], digest, config["storage_location_id"],
         f"{job['id']}/{artifact_id}", size, job["id"],
         _retention(store, "input", config.limits["artifact_retention_seconds"])))
    return artifact_id


# Refusals that come before the archive's safety checks: such an upload is
# never opened afterwards, since the portal's look-inside would decompress the
# bomb `archive-rejected` refused (surface D133).
UNOPENED = ("upload-digest-mismatch", "upload-too-large", "archive-rejected")


def referenced_elsewhere(store, row, excluding=()) -> bool:
    '''Whether a live artifact other than ``row`` and ``excluding`` still points at its bytes.

    An object is ``(location_id, storage_key)``, never the key alone: the
    same key in two locations is two objects.
    '''
    skip = {row["id"], *excluding}
    return store.one(
        f"SELECT 1 FROM artifacts WHERE location_id = ? AND storage_key = ? "
        f"AND deleted_at IS NULL AND id NOT IN ({', '.join('?' * len(skip))})",
        (row["location_id"], row["storage_key"], *skip)) is not None


def unopened(store, row, error_type: Optional[str]) -> bool:
    '''Whether ``row`` is the job's last upload, refused by one of `UNOPENED`.'''
    if row["kind"] != "input" or row["upload_seq"] is None or not error_type:
        return False
    if error_type.rsplit("/", 1)[-1] not in UNOPENED:
        return False
    last = store.one("SELECT max(upload_seq) AS n FROM artifacts WHERE job_id = ?",
                     (row["job_id"],))["n"]
    return row["upload_seq"] == last


def collect(store, storage, config, job, build_root) -> int:
    '''Index everything one finished job produced; returns how many rows.

    Idempotent: what was indexed as its node finished, or before a restart, is
    left alone.
    '''
    root = Path(build_root) / job["design"] / job["jobname"]

    location = config["storage_location_id"]
    floor = config.limits["artifact_retention_seconds"]
    written = 0

    # Before the build directory check: the run that leaves none is the run
    # whose record somebody needs.
    written += collect_staging(store, storage, config, job, build_root)
    written += collect_diagnostics(store, storage, config, job, build_root)

    if not root.is_dir():
        logger.warning(f"{job['id']} left no build directory to index")
        return written

    manifest = root / f"{job['design']}.pkg.json"
    written += _index(store, storage, job, location, floor, "manifest",
                      None, None, manifest, build_root)

    # SiliconCompiler's `job.log`, and nothing of this server's (surface D295).
    written += _index(store, storage, job, location, floor, "logs",
                      None, None, root / "job.log", build_root)

    # Every node again, for one whose archive was missed while the run went on.
    for node in store.all(
            'SELECT step, "index" FROM job_nodes WHERE job_id = ? ORDER BY step, "index"',
            (job["id"],)):
        written += collect_node(store, storage, config, job, build_root,
                                node["step"], node["index"])
        written += collect_diagnostics(store, storage, config, job, build_root,
                                       node["step"], node["index"])

    logger.info(f"indexed {written} artifacts for {job['id']}")
    return written


def collect_staging(store, storage, config, job, job_root) -> int:
    '''Index the job's `staging` record as it stands.

    Replaced, not added to: one row per job, repointed at the new bytes
    after each staging pass.'''
    source = Path(job_root) / record.STAGING_LOG
    try:
        handle = confine.open_inside(Path(job_root), source)
    except OSError:
        return 0

    object_id = str(uuid.uuid4())
    target = storage.artifact_dir(job["id"]) / object_id
    target.parent.mkdir(parents=True, exist_ok=True)
    # A fixed gzip time, so an unchanged record has the same digest.
    with handle, open(target, "wb") as raw, \
            gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as out:
        shutil.copyfileobj(handle, out)

    existing = store.one(
        "SELECT * FROM artifacts WHERE job_id = ? AND kind = 'staging' "
        "AND step IS NULL AND deleted_at IS NULL", (job["id"],))
    if existing is not None and existing["digest"] == _digest(target):
        target.unlink(missing_ok=True)
        return 0
    if existing is None:
        return _record(store, job, object_id, config["storage_location_id"],
                       config.limits["artifact_retention_seconds"], "staging", None,
                       None, target, "application/gzip")

    store.execute(
        "UPDATE artifacts SET digest = ?, storage_key = ?, size_bytes = ?, "
        "  location_id = ?, created_at = ? WHERE id = ?",
        (_digest(target), f"{job['id']}/{object_id}", target.stat().st_size,
         config["storage_location_id"], now(), existing["id"]))
    if not referenced_elsewhere(store, existing):
        storage.artifact_path(existing["storage_key"]).unlink(missing_ok=True)
    return 0


def collect_diagnostics(store, storage, config, job, job_root, step=None,
                        index=None) -> int:
    '''Index `record.diagnostics_files` for the job or one node, as one gzip tar.

    Not scrubbed, so never handed over the API (ladder row 3).'''
    if _exists(store, job, "diagnostics", step, index):
        return 0
    files = record.diagnostics_files(job_root, step, index)
    if not files:
        return 0

    artifact_id = str(uuid.uuid4())
    target = storage.artifact_dir(job["id"]) / artifact_id
    target.parent.mkdir(parents=True, exist_ok=True)
    added = 0
    try:
        with tarfile.open(target, "w:gz") as tar:
            for name, path in files:
                added += confine.add_file(tar, Path(job_root), path, name)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    if not added:
        target.unlink(missing_ok=True)
        return 0
    return _record(store, job, artifact_id, config["storage_location_id"],
                   config.limits["artifact_retention_seconds"], "diagnostics", step,
                   index, target, "application/gzip")


# What a node archive leaves out because the caller already has it: inputs/
# are upstream outputs, and sc_collected_files/ is the client's own upload,
# which it deletes on purpose as the largest thing in a build directory.
_NOT_IN_A_NODE = ("inputs", "sc_collected_files")


def _exists(store, job, kind, step, index) -> bool:
    '''Whether this kind is already indexed for this node.'''
    return store.one(
        'SELECT 1 FROM artifacts WHERE job_id = ? AND kind = ? '
        "AND step IS ? AND \"index\" IS ? LIMIT 1",
        (job["id"], kind, step, index)) is not None


def _index(store, storage, job, location, floor, kind, step, index,
           source: Path, root) -> int:
    '''Copy one file into the artifact store, if it is a regular file under ``root`` reached
    through no link.'''
    if _exists(store, job, kind, step, index):
        return 0
    try:
        handle = confine.open_inside(root, source)
    except OSError as e:
        if not isinstance(e, FileNotFoundError):
            logger.warning(f"{job['id']}: not indexing {source}: {e}")
        return 0

    artifact_id = str(uuid.uuid4())
    target = storage.artifact_dir(job["id"]) / artifact_id
    target.parent.mkdir(parents=True, exist_ok=True)

    with handle, gzip.open(target, "wb") as out:
        shutil.copyfileobj(handle, out)
    return _record(store, job, artifact_id, location, floor, kind, step, index,
                   target, "application/gzip")


def _log_archive(store, storage, job, location, floor, step, index, workdir: Path,
                 root) -> int:
    '''Index a node's `logs`: a gzip tar of its ``*.log`` files.'''
    if _exists(store, job, "logs", step, index):
        return 0
    try:
        names = sorted(child.name for child in workdir.iterdir()
                       if child.name.endswith(".log"))
    except OSError:
        return 0

    artifact_id = str(uuid.uuid4())
    target = storage.artifact_dir(job["id"]) / artifact_id
    target.parent.mkdir(parents=True, exist_ok=True)
    added = 0
    try:
        with tarfile.open(target, "w:gz") as tar:
            for name in names:
                added += confine.add_file(tar, root, workdir / name, name)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    if not added:
        target.unlink(missing_ok=True)
        return 0
    return _record(store, job, artifact_id, location, floor, "logs", step, index,
                   target, "application/gzip")


def log_text(storage, row) -> str:
    '''A `logs` artifact as text: the node's own log from its tar, or the job log.'''
    path = storage.artifact_path(row["storage_key"])
    if row["step"] is None:
        with gzip.open(path, "rt", errors="replace") as handle:
            return handle.read()
    with tarfile.open(path, "r:gz") as tar:
        members = [member for member in tar.getmembers() if member.isfile()]
        own = f"sc_{row['step']}_{row['index']}.log"
        member = next((m for m in members if m.name == own), members[0] if members else None)
        if member is None:
            return ""
        return tar.extractfile(member).read().decode(errors="replace")


def _real_dir(path: Path) -> bool:
    '''A directory, and not a link to one.'''
    return path.is_dir() and not path.is_symlink()


def _archive(store, storage, job, location, floor, kind, step, index,
             top: Path, base: Path, root, skip=(), job_tree=None, homes=None) -> int:
    '''Index a directory as one gzipped tar, relative to ``base``.

    Relative to the node's directory so a client unpacks it in place, which is
    why the contract has no per-artifact path. Links are stored, never followed.
    '''
    if _exists(store, job, kind, step, index):
        return 0

    artifact_id = str(uuid.uuid4())
    target = storage.artifact_dir(job["id"]) / artifact_id
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        with tarfile.open(target, "w:gz") as tar:
            confine.add_tree(tar, root, top, base, skip=skip, job_tree=job_tree,
                             homes=homes)
    except BaseException:
        target.unlink(missing_ok=True)
        raise

    return _record(store, job, artifact_id, location, floor, kind, step, index,
                   target, "application/gzip")


def _record(store, job, artifact_id, location, floor, kind, step, index,
            stored: Path, media_type: str) -> int:
    '''Write the row, or drop this copy if another thread already did.

    `_exists` cannot be enough: indexing runs on whichever request thread
    gets there first, and two can pass it together. The unique index decides.
    '''
    try:
        store.execute(
            'INSERT INTO artifacts (id, job_id, step, "index", digest, '
            "  location_id, storage_key, size_bytes, media_type, kind, "
            "  retained_until, provenance) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'declared')",
            (artifact_id, job["id"], step, index, _digest(stored), location,
             f"{job['id']}/{artifact_id}", stored.stat().st_size, media_type,
             kind, _retention(store, kind, floor)))
    except sqlite3.IntegrityError:
        logger.debug(f"{kind} for {step}/{index} was indexed by another "
                     "request; discarding this copy")
        stored.unlink(missing_ok=True)
        return 0

    return 1


def _digest(path: Path) -> str:
    return f"sha256:{file_digest(path).hexdigest()}"


def _retention(store, kind: str, floor_seconds: int) -> str:
    '''When this object ages out: the kind's own retention, never below the floor.'''
    from datetime import datetime, timedelta, timezone

    row = store.one("SELECT retention_seconds FROM artifact_kinds WHERE kind = ?",
                    (kind,))
    seconds = max(floor_seconds, (row["retention_seconds"] or 0) if row else 0)

    return stamp(datetime.now(timezone.utc) + timedelta(seconds=seconds))


# A gated `node` archive answers with its worst member's refusal (D120):
# permanent over transient.
_WORST = ("artifact-not-approved", "entitlement-denied", "not-ready")


def worst(refusals) -> Optional[str]:
    '''The worst of several ladder answers, or None when every one is.'''
    found = [refusal for refusal in refusals if refusal]
    for refusal in _WORST:
        if refusal in found:
            return refusal
    return found[0] if found else None


# Row 3's kinds: never over the API, read by an administrator in the portal.
NEVER_OVER_THE_API = ("issue", "diagnostics")


def ladder(row, surface_allows: bool = True,
           members: Optional[str] = None, admin: bool = False) -> Optional[str]:
    '''The refusal an artifact gets from the first ladder row that matches, or None.

    ``admin`` is the portal asking, where row 3's kinds are read. The ladder is
    entitlements.md's, with this profile's rows:

    ===  ==========================================  ======================
    1    ``deleted_at`` set                          ``not-found``
    2    ``withheld_at`` set                         ``artifact-not-approved``
    3    ``kind`` is ``issue`` or ``diagnostics``,   ``artifact-not-approved``
         over the API
    4    a ``node`` archive with a member that is    its WORST member's --
         not fetchable                               ``artifact-not-approved``,
                                                     then ``not-ready``
    --   this surface does not hand the kind over    ``artifact-not-approved``
         (``api_fetchable_kinds``)
    5    ``provenance = 'pending'``                  ``not-ready`` -- transient
    ===  ==========================================  ======================

    Rows 6-8 (grants) do not exist here: there is no approval machinery.
    `pending` is `not-ready`, never a `403` that would make a client abandon
    it; the surface row sits above so a kind never handed over is not *try
    again*. Retention passing is deliberately not a row: the reaper's
    ``deleted_at`` is row 1. Per caller, so computed, never stored.
    '''
    if row["deleted_at"]:
        return "not-found"
    if row["withheld_at"] or (row["kind"] in NEVER_OVER_THE_API and not admin):
        return "artifact-not-approved"
    if row["kind"] == "node" and members:
        # Held back only by a pending member is `not-ready` (D107).
        return members
    if not surface_allows:
        return "artifact-not-approved"
    if row["provenance"] == "pending":
        return "not-ready"
    return None


def fetchable(row, surface_allows: bool = True,
              members: Optional[str] = None, admin: bool = False) -> bool:
    '''Whether THIS caller may have the bytes: the ladder, with no refusal.'''
    return ladder(row, surface_allows, members, admin) is None


def cause(row) -> Optional[str]:
    """Whether the bytes were ``expired`` (reaper) or ``removed`` (a person), or None.

    `deleted_by` decides it and stays off the wire: it names a user.
    """
    if not row["deleted_at"]:
        return None
    return "removed" if row["deleted_by"] else "expired"


def wire(row, surface_allows: bool = True,
         members: Optional[str] = None, admin: bool = False) -> Dict[str, Any]:
    '''One artifact, as §21 publishes it.'''
    return {
        "id": row["id"],
        "step": row["step"],
        "index": row["index"],
        "kind": row["kind"],
        "media_type": row["media_type"],
        "size_bytes": row["size_bytes"],
        "digest": row["digest"],
        "created_at": row["created_at"],
        # null under a legal hold: no scheduled expiry.
        "retained_until": None if row["legal_hold_at"] else row["retained_until"],
        "deleted_at": row["deleted_at"],
        # A closed enum for a client to branch on, and prose for a person:
        # `deleted_at` alone cannot tell expiry from removal.
        "deleted_cause": cause(row),
        "deleted_reason": row["deleted_reason"],
        "fetchable": fetchable(row, surface_allows, members, admin),
        # Required, though this profile takes no access requests (surface D177).
        "access_requested_at": None,
        # Always false: an unauthenticated deployment offers no way to ask
        # (surface D309).
        "can_request_access": False,
    }
    # No `blocked_by`: this deployment has no agreements.
