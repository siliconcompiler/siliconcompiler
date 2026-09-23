'''
What a finished run left behind, as rows.

🔴 **The results tarball does not disappear -- it stops being an endpoint and
becomes an artifact.** The old server answered `get_results` with one archive
per node and no record of it; a tarball is not a row, so it carries no kind, no
retention and no per-object gate. Here every object is indexed, and the listing
is the answer to *where did my results go* even when the bytes are gone.

Four kinds are produced, and each file has exactly one home:

``manifest``  the job's own ``<design>.pkg.json``. Job-level, so no step. **The
              kind most likely to be the only one there is**: it is small, and
              it carries the record -- node states, metrics, tool versions --
              so *what happened* is answerable with no outputs on disk at all
``logs``      one node's ``sc_<step>_<index>.log``, as text. This is what
              ``GET /v1/jobs/{id}/logs`` redirects to, which is why it stays a
              readable file rather than being folded into an archive
``reports``   that node's ``reports/``. Also inside ``outputs``, and separate on
              purpose: the two kinds have different default policies, so a
              caller who may have one and not the other still gets its metrics
``outputs``   *everything a node produced, intermediates included* -- the node's
              working directory minus ``inputs/``, which holds nothing but
              copies of the upstream node's outputs

``input`` is deliberately not produced. It is the archive the client uploaded,
the client still has it, and keeping a second copy costs the whole upload again
for something nobody fetches.
'''

import hashlib
import logging
import shutil
import tarfile

from pathlib import Path
from typing import Any, Dict, List, Optional

from siliconcompiler.remote.server.ids import uuid7
from siliconcompiler.remote.server.store import now

__all__ = ["collect", "collect_node_log", "wire", "fetchable", "KINDS"]


logger = logging.getLogger("sc-server")


# The eight are the contract's; these four are what this deployment produces.
KINDS = ("manifest", "logs", "reports", "outputs")

_CHUNK = 1024 * 1024


def collect_node_log(store, storage, config, job, build_root, step, index) -> int:
    '''Index one node's log, the moment that node is done.

    🔴 Not deferrable to the end of the job. A terminal node answers `/logs`
    with a `303` to its archived log, and a node finishing while the rest of the
    flow runs on is the ORDINARY case -- it is exactly what happens to somebody
    tailing that node. Waiting for the job would answer *no log was kept* for a
    node that had just written one.
    '''
    root = Path(build_root) / job["design"] / job["jobname"]
    log = root / step / index / f"sc_{step}_{index}.log"
    if not log.is_file():
        return 0

    return _index(store, storage, job, config["storage_location_id"],
                  config.limits["job_retention_days"], "logs", step, index,
                  log, "text/plain")


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

    for node in store.all(
            'SELECT step, "index" FROM job_nodes WHERE job_id = ? ORDER BY step, "index"',
            (job["id"],)):
        step, index = node["step"], node["index"]
        workdir = root / step / index
        if not workdir.is_dir():
            # A node that never ran leaves nothing, which is a true answer and
            # not an error: its state already says so.
            continue

        log = workdir / f"sc_{step}_{index}.log"
        if log.is_file():
            written += _index(store, storage, job, location, floor, "logs",
                              step, index, log, "text/plain")

        reports = workdir / "reports"
        if _has_files(reports):
            written += _archive(store, storage, job, location, floor, "reports",
                                step, index, [reports], workdir)

        # `inputs/` is excluded: it is copies of the upstream node's outputs,
        # which the caller is getting from the upstream node.
        produced = [child for child in sorted(workdir.iterdir())
                    if child.name != "inputs"]
        if produced:
            written += _archive(store, storage, job, location, floor, "outputs",
                                step, index, produced, workdir)

    logger.info(f"indexed {written} artifacts for {job['id']}")
    return written


def _has_files(path: Path) -> bool:
    return path.is_dir() and any(path.rglob("*"))


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
             members: List[Path], base: Path) -> int:
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
            tar.add(member, arcname=str(member.relative_to(base)))

    return _record(store, job, artifact_id, location, floor, kind, step, index,
                   target, "application/gzip")


def _record(store, job, artifact_id, location, floor, kind, step, index,
            stored: Path, media_type: str) -> int:
    store.execute(
        'INSERT INTO artifacts (id, job_id, step, "index", content_hash, '
        "  location_id, storage_key, size_bytes, media_type, kind, "
        "  retention_until, provenance) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'declared')",
        (artifact_id, job["id"], step, index, _digest(stored), location,
         f"{job['id']}/{artifact_id}", stored.stat().st_size, media_type, kind,
         _retention(store, kind, floor)))
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
