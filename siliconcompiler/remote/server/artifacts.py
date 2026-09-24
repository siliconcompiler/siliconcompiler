'''
What a finished run left behind, as rows.

🔴 **The results tarball does not disappear -- it stops being an endpoint and
becomes an artifact.** The old server answered `get_results` with one archive
per node and no record of it; a tarball is not a row, so it carries no kind, no
retention and no per-object gate. Here every object is indexed, and the listing
is the answer to *where did my results go* even when the bytes are gone.

Three kinds are produced, and every byte is stored once:

``manifest``  the job's own ``<design>.pkg.json``. Job-level, so no step. **The
              kind most likely to be the only one there is**: it is small, and
              it carries the record -- node states, metrics, tool versions --
              so *what happened* is answerable with no outputs on disk at all
``logs``      one node's ``sc_<step>_<index>.log``, as text. This is what
              ``GET /v1/jobs/{id}/logs`` redirects to, which is why it stays a
              readable file rather than only living inside the bundle
``bundle``    🔴 **one node's whole working directory, indexed the moment that
              node finishes.** *"The results tarball does not disappear -- it
              stops being an endpoint and becomes an artifact, assembled during
              the run and indexed like everything else."* Per node rather than
              per job precisely so that it IS assembled during the run: a
              client can take each node's results as they appear instead of
              waiting for the last node to decide whether the first one's work
              is available.

⚠️ **`outputs` and `reports` are deliberately NOT produced, and that is a
choice with a cost.** They would be a second copy of bytes the bundle already
holds -- on this deployment roughly doubling what a job occupies. What it buys
elsewhere is that a bundle is **never grantable**, so on a deployment with
approvals a caller who may not have the bundle could still be given its reports.
There is no approval machinery here and the only caller who can see a job is its
owner, so nobody is losing anything that exists. ✅ **A client asking
``?kind=reports`` gets an empty list, which is the true answer:** *this server
does not index those*.

``input`` is not produced either. It is the archive the client uploaded, the
client still has it, and keeping a second copy costs the whole upload again for
something nobody fetches.
'''

import hashlib
import logging
import shutil
import sqlite3
import tarfile

from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional

from siliconcompiler.remote.server.ids import uuid7
from siliconcompiler.remote.server.store import now

__all__ = ["collect", "collect_node", "wire", "fetchable", "KINDS"]


logger = logging.getLogger("sc-server")


# The eight are the contract's; these four are what this deployment produces.
KINDS = ("manifest", "logs", "bundle")

_CHUNK = 1024 * 1024


def collect_node(store, storage, config, job, build_root, step, index) -> int:
    '''Index one node's results, the moment that node is done.

    🔴 Not deferrable to the end of the job, and for two reasons. A terminal
    node answers `/logs` with a `303` to its archived log, and a node finishing
    while the rest of the flow runs on is the ORDINARY case -- waiting for the
    job would answer *no log was kept* for a node that had just written one.
    And the bundle carries that node's manifest, so a client that takes it as
    it appears has the run's record, metrics included, while the run is still
    going.
    '''
    workdir = Path(build_root) / job["design"] / job["jobname"] / step / index
    if not workdir.is_dir():
        return 0

    location = config["storage_location_id"]
    floor = config.limits["job_retention_days"]
    written = 0

    log = workdir / f"sc_{step}_{index}.log"
    if log.is_file():
        written += _index(store, storage, job, location, floor, "logs",
                          step, index, log, "text/plain")

    members = [child for child in sorted(workdir.iterdir())
               if child.name not in _NOT_IN_A_BUNDLE]
    if members:
        written += _archive(store, storage, job, location, floor, "bundle",
                            step, index, members, workdir,
                            exclude=_bundle_filter)

    return written


def collect(store, storage, config, job, build_root) -> int:
    '''Index everything one finished job produced. Returns how many rows.

    Called when the job reaches a terminal state. Every write is conditional on
    there being no row for that kind and node yet, so the node logs already
    indexed as their nodes finished are left alone, and a second call after a
    restart adds nothing rather than duplicating the listing.
    '''
    root = Path(build_root) / job["design"] / job["jobname"]
    if not root.is_dir():
        logger.warning(f"{job['id']} left no build directory to index")
        return 0

    location = config["storage_location_id"]
    floor = config.limits["job_retention_days"]
    written = 0

    manifest = root / f"{job['design']}.pkg.json"
    if manifest.is_file():
        written += _index(store, storage, job, location, floor, "manifest",
                          None, None, manifest, "application/json")

    # The run's own job log, which belongs to no node. Job-level `logs`, since
    # that is exactly what it is.
    for job_log in sorted(root.glob("job.*.log")):
        written += _index(store, storage, job, location, floor, "logs",
                          None, None, job_log, "text/plain")
        break

    # Every node again, because a node whose bundle was missed while the run
    # was going still has to be indexed -- the nodes that were caught cost one
    # SELECT each and write nothing.
    for node in store.all(
            'SELECT step, "index" FROM job_nodes WHERE job_id = ? ORDER BY step, "index"',
            (job["id"],)):
        written += collect_node(store, storage, config, job, build_root,
                                node["step"], node["index"])

    logger.info(f"indexed {written} artifacts for {job['id']}")
    return written


# What a bundle leaves out, and every one of them for the same reason: the
# caller already has it, or it is this server talking to itself.
#
#   inputs/              copies of the upstream node's outputs, which are in
#                        here already under the node that produced them
#   sc_collected_files/  what the CLIENT uploaded. It deletes its own copy once
#                        the archive is built, deliberately -- it is the largest
#                        thing in a build directory -- so sending it back
#                        undoes that and pays for the same bytes twice
_NOT_IN_A_BUNDLE = ("inputs", "sc_collected_files")


def _bundle_filter(info: "tarfile.TarInfo"):
    '''Drop the excluded directories wherever they appear in the tree.'''
    parts = PurePosixPath(info.name).parts
    return None if any(part in _NOT_IN_A_BUNDLE for part in parts) else info


def _exists(store, job, kind, step, index) -> bool:
    '''Whether this kind is already indexed for this node.

    One row per (job, kind, node) is the rule that makes indexing idempotent,
    and it is checked here rather than by the callers so that no path can
    forget it.
    '''
    return store.one(
        'SELECT 1 FROM artifacts WHERE job_id = ? AND kind = ? '
        "AND step IS ? AND \"index\" IS ? LIMIT 1",
        (job["id"], kind, step, index)) is not None


def _index(store, storage, job, location, floor, kind, step, index,
           source: Path, media_type: str) -> int:
    '''One file, copied into the artifact store and recorded.'''
    if _exists(store, job, kind, step, index):
        return 0

    artifact_id = str(uuid7())
    target = storage.artifact_dir(job["id"]) / artifact_id
    target.parent.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(source, target)
    return _record(store, job, artifact_id, location, floor, kind, step, index,
                   target, media_type)


def _archive(store, storage, job, location, floor, kind, step, index,
             members: List[Path], base: Path, exclude=None) -> int:
    '''Several paths, as one gzipped tar, recorded as one artifact.

    Stored relative to the node's working directory, so a client unpacks it
    straight into the same place without knowing anything about this server's
    layout -- which is the reason the contract has no per-artifact path.
    '''
    if _exists(store, job, kind, step, index):
        return 0

    artifact_id = str(uuid7())
    target = storage.artifact_dir(job["id"]) / artifact_id
    target.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(target, "w:gz") as tar:
        for member in members:
            tar.add(member, arcname=str(member.relative_to(base)), filter=exclude)

    return _record(store, job, artifact_id, location, floor, kind, step, index,
                   target, "application/gzip")


def _record(store, job, artifact_id, location, floor, kind, step, index,
            stored: Path, media_type: str) -> int:
    '''Write the row, or find that somebody else already did.

    🔴 The `_exists` check above is not enough and cannot be made enough:
    indexing runs on whichever request thread gets there first, and a client
    polling its job while tailing two logs has three of them. Two that check
    together both pass. The unique index is what actually decides, and this is
    where losing is handled -- by dropping the bytes this thread wrote, since
    the winner's copy is the one the row points at.
    '''
    try:
        store.execute(
            'INSERT INTO artifacts (id, job_id, step, "index", content_hash, '
            "  location_id, storage_key, size_bytes, media_type, kind, "
            "  retention_until, provenance) "
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
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _retention(store, kind: str, floor_days: int) -> str:
    '''When this object ages out.

    `limits.job_retention_days` is the floor EVERY artifact gets and not the
    whole answer: retention is per kind, so a manifest and the outputs beside it
    go at different times. A kind with no number of its own takes the floor.
    '''
    from datetime import datetime, timedelta, timezone

    row = store.one("SELECT retention_days FROM artifact_kinds WHERE kind = ?", (kind,))
    days = max(floor_days, (row["retention_days"] or 0) if row else 0)

    when = datetime.now(timezone.utc) + timedelta(days=days)
    return when.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def fetchable(row) -> bool:
    '''Whether THIS caller may have the bytes.

    🔴 Per caller, never cached across callers -- which is why it is computed
    rather than stored. On this deployment the answer is the same for everybody
    who can see the job, because there is no approval machinery here and the
    only caller who can see a job is its owner. What is left are the three
    reasons the bytes are not available to anyone: deleted, withheld, or aged
    out.
    '''
    if row["deleted_at"] or row["withheld_at"]:
        return False
    return not _passed(row["retention_until"])


def _passed(when: Optional[str]) -> bool:
    return bool(when) and when <= now()


def wire(row) -> Dict[str, Any]:
    '''One artifact, as §21 publishes it.'''
    return {
        "id": row["id"],
        "step": row["step"],
        "index": row["index"],
        "kind": row["kind"],
        "media_type": row["media_type"],
        "size_bytes": row["size_bytes"],
        "content_hash": row["content_hash"],
        "created_at": row["created_at"],
        # null means held indefinitely -- a legal hold has no expiry to state.
        "expires_at": None if row["legal_hold_at"] else row["retention_until"],
        # non-null means the bytes are gone and the row is not. Distinct from
        # expires_at passing: retention lapsing is the system doing what it
        # said, a deleted_at is somebody deciding.
        "deleted_at": row["deleted_at"],
        "fetchable": fetchable(row),
    }
    # No `blocked_by` and no `access_request_url`: both are about an agreement
    # standing in the way, and this deployment has no agreements. An
    # unauthenticated deployment never emits access_request_url, because an
    # endpoint that always refuses is worse than an absent one.
