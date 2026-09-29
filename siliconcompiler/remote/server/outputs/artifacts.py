'''
What a finished run left behind, as rows.

🔴 **The results tarball does not disappear -- it stops being an endpoint and
becomes an artifact.** The old server answered `get_results` with one archive
per node and no record of it; a tarball is not a row, so it carries no kind, no
retention and no per-object gate. Here every object is indexed, and the listing
is the answer to *where did my results go* even when the bytes are gone.

Five kinds are produced, and every byte is stored once:

Every artifact is stored and served gzipped (surface §21).

``manifest``  the job's own ``<design>.pkg.json``, gzipped. Job-level, so no step. **The
              kind most likely to be the only one there is**: it is small, and
              it carries the record -- node states, metrics, tool versions --
              so *what happened* is answerable with no outputs on disk at all
``logs``      one node's log files, as a gzip tar with paths relative to
              the node's directory. A finished node's stream names it.
              **One more is job-level**: the run's own account of itself, which
              is ``job.log`` where the flow got far enough to write one and the
              server's ``sc-server-run.log`` where it did not -- see
              ``_the_run_itself``
``node``      🔴 **one node's whole working directory, indexed the moment that
              node finishes.** *"The results tarball does not disappear -- it
              stops being an endpoint and becomes an artifact, assembled during
              the run and indexed like everything else."* Per node rather than
              per job precisely so that it IS assembled during the run: a
              client can take each node's results as they appear instead of
              waiting for the last node to decide whether the first one's work
              is available.

              🔴 **It is ALWAYS bound to a step and an index, and there is no
              job-level one.** The kind is named for the thing it is, so a row
              of this kind with no coordinates would be a contradiction rather
              than a broader archive.
``reports``   one node's ``reports/`` directory, as its own archive. 🔴 **A
              second copy of bytes the node archive already holds, and that is
              the point rather than an oversight.** A node's reports are
              kilobytes and its whole working directory is often gigabytes, so
              above ``limits.max_download_bytes`` the node archive is refused
              outright while the reports are still served -- which is the case
              this kind exists for. On a deployment with approvals it is also
              the object that can be granted when the whole node cannot.

⚠️ **The cost, stated: roughly what the reports occupy, twice.** Measured
rather than assumed -- on an asicflow node it is the difference between the
node archive and the node archive plus a few hundred kilobytes, because the
heavy things in a working directory are the DEF and the database, not the
reports.

⚠️ **`outputs` is still deliberately NOT produced.** THAT would be a second
copy of the large half.

``input``     🆕 **what went IN, so it can be inspected.** Two shapes:

              - **job-level, one per upload.** Every archive the server
                accepted into the job -- the first, and each follow-up a job
                sent back for its sources carries -- is its own row, in the
                order they arrived, with the digest the submit verified as its
                hash. Kept even when the job is then refused, which is when
                somebody wants to see what was sent. **Not a copy**: the upload
                is MOVED into the store rather than deleted, so the cost is the
                upload itself, held for the kind's retention.
              - **one node's ``inputs/``**, bound to the node: what its
                upstream handed it. Links are followed, so the archive holds the
                bytes the node read.

              ⚠️ **Neither is a member of the node archive** -- that leaves
              ``inputs/`` out -- so neither decides whether it may be fetched.
              And the client fetches neither: it has its upload, and a node's
              inputs are its upstream's outputs, which it already takes.

⚠️ **A `node` artifact IS grantable, and this deployment has nothing to grant
with.** Where a server does, the way to hold one back is ``withheld_at``, which
lowers the derived policy without claiming the bytes are gone. 🔴 And an
``issue`` at a node's coordinates is excluded from what a node archive is
considered to contain, by kind: ``issue`` is never fetchable, so a ladder that
derived a node's entitlement from everything at its coordinates would make one
click of a generate-an-issue button turn a node archive undownloadable over a
file that is not inside it. Nothing here derives that ladder -- ``fetchable``
is per row -- so the exclusion is a note for the deployment that does.
'''

import gzip
import hashlib
import logging
import os
import shutil
import sqlite3
import tarfile

from pathlib import Path
from typing import Any, Dict, Optional

from siliconcompiler.remote import links
from siliconcompiler.remote.server.outputs import confine
from siliconcompiler.remote.server.running.dispatch import RUN_LOG
from siliconcompiler.remote.server.state.ids import uuid7

__all__ = ["collect", "collect_node", "cause", "wire", "fetchable", "KINDS", "log_text",
           "referenced_elsewhere"]


logger = logging.getLogger("sc-server")


# The eight are the contract's; these four are what this deployment produces.
# Expected of the profile: manifest, logs, reports, node. Optional: input,
# outputs, final, issue -- `input` moved there because the owner already has
# the bytes it would hold, which is what `artifact_kinds` had said all along.
KINDS = ("manifest", "logs", "reports", "node")

_CHUNK = 1024 * 1024


def collect_node(store, storage, config, job, build_root, step, index) -> int:
    '''Index one node's results, the moment that node is done.

    🔴 Not deferrable to the end of the job, and for two reasons. A terminal
    node answers `/logs` with a `303` to its archived log, and a node finishing
    while the rest of the flow runs on is the ORDINARY case -- waiting for the
    job would answer *no log was kept* for a node that had just written one.
    And the node archive carries that node's manifest, so a client that takes
    it as it appears has the run's record, metrics included, while the run is
    still going.
    '''
    workdir = Path(build_root) / job["design"] / job["jobname"] / step / index
    if not workdir.is_dir():
        return 0

    location = config["storage_location_id"]
    floor = config.limits["job_retention_days"]
    written = 0

    # 🔴 Every read below is confined to the job's own tree (see `confine`):
    # a node's code can leave a link anywhere in its working directory, and
    # following one would index the host's files as the job's results.
    root = Path(build_root)
    # Where a link may end, and every hard-linked file's home, walked once for
    # this node's archives (database D142).
    job_tree = root / job["design"] / job["jobname"]
    homes = links.Homes(job_tree)

    written += _log_archive(store, storage, job, location, floor, step, index,
                            workdir, root)

    # 🔴 The node's own manifest, on its own and bound to the node, beside the
    # job's. It is what carries that node's record and metrics -- with the
    # journal a client replays them from -- so a deployment that hands over
    # manifests and no bulk output can still show a finished node's runtime,
    # warnings and errors while the rest of the run goes on. Inside the node
    # archive only, it went wherever the archive went, and a server that
    # withholds archives withheld the record with them.
    #
    # ⚠️ It is a second copy of a file the node archive holds, a few MB per
    # node. A client with the archive does not fetch it twice.
    manifest = workdir / "outputs" / f"{job['design']}.pkg.json"
    written += _index(store, storage, job, location, floor, "manifest",
                      step, index, manifest, "application/json", root)

    # 🔴 Indexed before the node archive, not after. If a node finishes and
    # something goes wrong partway through indexing it, the small object a
    # person actually reads is the one already written.
    reports = workdir / "reports"
    if _real_dir(reports) and any(reports.iterdir()):
        written += _archive(store, storage, job, location, floor, "reports",
                            step, index, reports, workdir, root, job_tree=job_tree,
                            homes=homes)

    # 🔴 A link inside the job stays a link, pointed at the file's real home:
    # a task's pass-through output becomes one link to the upstream node's
    # `outputs/`. So a node archive is not self-contained -- a passed-through
    # file resolves where its home node is unpacked beside it -- and nothing
    # is copied in place of a link (contract.md; database D142).
    if any(child.name not in _NOT_IN_A_NODE for child in workdir.iterdir()):
        written += _archive(store, storage, job, location, floor, "node",
                            step, index, workdir, workdir, root, skip=_NOT_IN_A_NODE,
                            job_tree=job_tree, homes=homes)

    # What the node was handed, on its own: the node archive leaves it out, and
    # it is what somebody debugging the node wants to read -- links to the
    # upstream outputs it was handed, never their bytes.
    inputs = workdir / "inputs"
    if _real_dir(inputs) and any(inputs.iterdir()):
        written += _archive(store, storage, job, location, floor, "input",
                            step, index, inputs, workdir, root, job_tree=job_tree,
                            homes=homes)

    return written


def record_upload(store, storage, config, job, upload: Path, digest: str,
                  size: int) -> str:
    '''One upload, kept as a job-level `input` numbered by `upload_seq`.
    Returns its id.

    **Moved, not copied**: the upload was going to be deleted, and the bytes
    are the artifact. The hash is what storage reports for them, which submit
    compares with the declared digest.
    '''
    artifact_id = str(uuid7())
    target = storage.artifact_dir(job["id"]) / artifact_id
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(upload, target)

    store.execute(
        'INSERT INTO artifacts (id, job_id, step, "index", content_hash, '
        "  location_id, storage_key, size_bytes, media_type, kind, upload_seq, "
        "  retention_until, provenance) "
        "VALUES (?, ?, NULL, NULL, ?, ?, ?, ?, 'application/gzip', 'input', "
        "  (SELECT coalesce(max(upload_seq), 0) + 1 FROM artifacts WHERE job_id = ?), "
        "  ?, 'declared')",
        (artifact_id, job["id"], digest, config["storage_location_id"],
         f"{job['id']}/{artifact_id}", size, job["id"],
         _retention(store, "input", config.limits["job_retention_days"])))
    return artifact_id


# Refusals that come before an upload's archive has passed its safety checks:
# an upload refused with one of these was never opened, and is never opened
# afterwards -- the portal's look-inside decompresses the whole archive, which
# is the bomb `archive-rejected` refused (surface D133).
UNOPENED = ("upload-digest-mismatch", "upload-too-large", "archive-rejected")


def referenced_elsewhere(store, row, excluding=()) -> bool:
    '''Whether a live artifact other than ``row`` -- and those ``excluding``
    names -- still points at its bytes.

    🔴 **An object is ``(location_id, storage_key)``**, never the key alone: the
    same key in two locations is two objects, and counting across them would
    keep one forever or reap the other from under its row. Reclaiming bytes
    is refcounted on the pair.
    '''
    skip = {row["id"], *excluding}
    return store.one(
        f"SELECT 1 FROM artifacts WHERE location_id = ? AND storage_key = ? "
        f"AND deleted_at IS NULL AND id NOT IN ({', '.join('?' * len(skip))})",
        (row["location_id"], row["storage_key"], *skip)) is not None


def unopened(store, row, error_type: Optional[str]) -> bool:
    '''Whether ``row`` is an upload that must not be opened: the job's last,
    refused by one of `UNOPENED`. Every refused upload is the last one, since
    a refusal ends the job.'''
    if row["kind"] != "input" or row["upload_seq"] is None or not error_type:
        return False
    if error_type.rsplit("/", 1)[-1] not in UNOPENED:
        return False
    last = store.one("SELECT max(upload_seq) AS n FROM artifacts WHERE job_id = ?",
                     (row["job_id"],))["n"]
    return row["upload_seq"] == last


def collect(store, storage, config, job, build_root) -> int:
    '''Index everything one finished job produced. Returns how many rows.

    Called when the job reaches a terminal state. Every write is conditional on
    there being no row for that kind and node yet, so the node logs already
    indexed as their nodes finished are left alone, and a second call after a
    restart adds nothing rather than duplicating the listing.
    '''
    root = Path(build_root) / job["design"] / job["jobname"]

    location = config["storage_location_id"]
    floor = config.limits["job_retention_days"]
    written = 0

    # 🔴 Before the build directory is checked for, and that ordering is the
    # whole point: the run that leaves no build directory is the run whose log
    # somebody needs.
    account = _the_run_itself(Path(build_root), root)
    if account is not None:
        written += _index(store, storage, job, location, floor, "logs",
                          None, None, account, "text/plain", build_root)

    if not root.is_dir():
        logger.warning(f"{job['id']} left no build directory to index")
        return written

    manifest = root / f"{job['design']}.pkg.json"
    written += _index(store, storage, job, location, floor, "manifest",
                      None, None, manifest, "application/json", build_root)

    # Every node again, because a node whose archive was missed while the run
    # was going still has to be indexed -- the nodes that were caught cost one
    # SELECT each and write nothing.
    for node in store.all(
            'SELECT step, "index" FROM job_nodes WHERE job_id = ? ORDER BY step, "index"',
            (job["id"],)):
        written += collect_node(store, storage, config, job, build_root,
                                node["step"], node["index"])

    logger.info(f"indexed {written} artifacts for {job['id']}")
    return written


def collect_run_log(store, storage, config, job, build_root) -> int:
    '''Index the job-level `logs` alone: for a job that ends before it runs,
    such as one whose staging failed.'''
    account = _the_run_itself(Path(build_root),
                              Path(build_root) / job["design"] / job["jobname"])
    if account is None:
        return 0
    return _index(store, storage, job, config["storage_location_id"],
                  config.limits["job_retention_days"], "logs", None, None, account,
                  "text/plain", build_root)


# The job-level `logs`, as the server assembles it: its own record of the job,
# then the flow's. In the job root, beside the progress file.
JOB_LOG = "sc-server-job.log"


def _the_run_itself(job_root: Path, build_dir: Path) -> Optional[Path]:
    '''The one log that belongs to the run rather than to any node.

    🔴 **Both accounts, in one file: this server's record of the job first --
    staging, what the install added (profile §5), the run's own stdout, an
    image that would not pull -- then the flow's `job.log`.** It used to be one
    or the other, `job.log` wherever the flow wrote one, so anything written to
    the run log was lost on every job whose flow started: a host install's
    record included (database D143).

    ⚠️ **One artifact, never two**, and the constraint is the contract's: an
    artifact is identified by `(job, kind, step, index)` and carries no name on
    the wire, so two job-level `logs` rows reach a client as two objects it
    cannot tell apart. The two files are nearly disjoint by design --
    `_silence_console` keeps the flow's output out of the run log -- so
    together they are the whole account, and nothing is said twice.

    🔴 Both are reached through the JOB root and not the build directory.
    `job.log` sits beside the nodes at `<design>/<jobname>/`, is the job's own
    file, and is read through `confine`; the run log is one level up, beside
    the batch script, because the scheduler wrote it before anything knew a
    design name.
    '''
    parts = []
    run_log = job_root / RUN_LOG
    if run_log.is_file() and not run_log.is_symlink():
        parts.append(("the server's record of this job", run_log))
    current = build_dir / "job.log"
    if current.is_file():
        parts.append(("job.log", current))
    if not parts:
        return None

    combined = job_root / JOB_LOG
    partial = job_root / f"{JOB_LOG}.part"
    with open(partial, "wb") as out:
        for title, path in parts:
            out.write(f"==> {title} <==\n".encode())
            try:
                with confine.open_inside(job_root, path) as source:
                    shutil.copyfileobj(source, out)
            except OSError:
                out.write(b"(it could not be read)\n")
            out.write(b"\n")
    os.replace(partial, combined)
    return combined


# What a node archive leaves out, and every one of them for the same reason:
# the caller already has it, or it is this server talking to itself.
#
#   inputs/              copies of the upstream node's outputs, which are in
#                        here already under the node that produced them
#   sc_collected_files/  what the CLIENT uploaded. It deletes its own copy once
#                        the archive is built, deliberately -- it is the largest
#                        thing in a build directory -- so sending it back
#                        undoes that and pays for the same bytes twice
_NOT_IN_A_NODE = ("inputs", "sc_collected_files")


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
           source: Path, media_type: str, root) -> int:
    '''One file, copied into the artifact store and recorded -- where it is a
    regular file under ``root`` reached through no link.'''
    if _exists(store, job, kind, step, index):
        return 0
    try:
        handle = confine.open_inside(root, source)
    except OSError as e:
        if not isinstance(e, FileNotFoundError):
            logger.warning(f"{job['id']}: not indexing {source}: {e}")
        return 0

    artifact_id = str(uuid7())
    target = storage.artifact_dir(job["id"]) / artifact_id
    target.parent.mkdir(parents=True, exist_ok=True)

    # 🔴 Every artifact is stored and served gzipped (surface §21).
    with handle, gzip.open(target, "wb") as out:
        shutil.copyfileobj(handle, out)
    return _record(store, job, artifact_id, location, floor, kind, step, index,
                   target, "application/gzip")


def _log_archive(store, storage, job, location, floor, step, index, workdir: Path,
                 root) -> int:
    '''A node's `logs`: a gzip tar of its log files, by name relative to the
    node's directory. None where the node left no log.'''
    if _exists(store, job, "logs", step, index):
        return 0
    try:
        names = sorted(child.name for child in workdir.iterdir()
                       if child.name.endswith(".log"))
    except OSError:
        return 0

    artifact_id = str(uuid7())
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
    '''A `logs` artifact as text: the node's SiliconCompiler log out of its
    tar, or a job-level log out of its gzip.'''
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
    '''A directory, as one gzipped tar, recorded as one artifact.

    Stored relative to the node's working directory, so a client unpacks it
    straight into the same place without knowing anything about this server's
    layout -- which is the reason the contract has no per-artifact path. Read
    through `confine`, so a link is stored as a link, pointed at its file's
    home inside ``job_tree``, and never followed.
    '''
    if _exists(store, job, kind, step, index):
        return 0

    artifact_id = str(uuid7())
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


# A gated `node` archive answers with its worst member's refusal (D120), and
# worst is this order: a permanent refusal over a transient one.
_WORST = ("artifact-not-approved", "entitlement-denied", "not-ready")


def worst(refusals) -> Optional[str]:
    '''The worst of several ladder answers, or None when every one is.'''
    found = [refusal for refusal in refusals if refusal]
    for refusal in _WORST:
        if refusal in found:
            return refusal
    return found[0] if found else None


def ladder(row, surface_allows: bool = True,
           members: Optional[str] = None) -> Optional[str]:
    '''The refusal an artifact gets, by the first row of the ladder that
    matches -- or None when the caller may have the bytes.

    The ladder is entitlements.md's, in its order, with this profile's rows:

    ===  ==========================================  ======================
    1    ``deleted_at`` set                          ``not-found``
    2    ``withheld_at`` set                         ``artifact-not-approved``
    3    ``kind = 'issue'``                          ``artifact-not-approved``
    4    a ``node`` archive with a member that is    its WORST member's --
         not fetchable                               ``artifact-not-approved``,
                                                     then ``not-ready``
    --   this surface does not hand the kind over    ``artifact-not-approved``
         (``api_fetchable_kinds``)
    5    ``provenance = 'pending'``                  ``not-ready`` -- transient
    ===  ==========================================  ======================

    🔴 **Rows 6-8 -- grants, the resources an artifact derives from -- do not
    exist here**: there is no approval machinery, and the only caller who can
    see a job is its owner.

    🔴 **`pending` is `not-ready` and never a permanent refusal.** It is still
    being described, and answering it `403` told a client to abandon an
    artifact that would shortly be fetchable. The surface row sits above it so
    that a kind this surface never hands over is not answered *try again*.

    ⚠️ **Retention passing is deliberately not a row.** The reaper follows it by
    setting ``deleted_at``, which is row 1; between the instant and the sweep
    the bytes are still here and still fetchable -- a promise to keep data at
    least that long says nothing about the minute after it. This used to answer
    *not fetchable* the moment the date passed.

    Per caller, never cached across callers -- which is why it is computed
    rather than stored.
    '''
    if row["deleted_at"]:
        return "not-found"
    if row["withheld_at"] or row["kind"] == "issue":
        return "artifact-not-approved"
    if row["kind"] == "node" and members:
        # 🔴 Withholding a member withholds the archive, and an archive held
        # back only by a PENDING member is `not-ready` -- the D107 mistake one
        # level down answered it a permanent `artifact-not-approved`.
        return members
    if not surface_allows:
        return "artifact-not-approved"
    if row["provenance"] == "pending":
        return "not-ready"
    return None


def fetchable(row, surface_allows: bool = True,
              members: Optional[str] = None) -> bool:
    '''Whether THIS caller may have the bytes: the ladder, with no refusal.'''
    return ladder(row, surface_allows, members) is None


def cause(row) -> Optional[str]:
    """Which of the two ways the bytes went, or None while they are here.

    🔴 **`deleted_by` decides it and `deleted_by` is not on the wire** -- it
    names a user, which is a fact about an account and not about the object.
    NULL is the reaper, which is retention doing what it said it would; set is
    a person, which is somebody deciding. Those are the only two ways an
    artifact loses its bytes.
    """
    if not row["deleted_at"]:
        return None
    return "removed" if row["deleted_by"] else "expired"


def wire(row, surface_allows: bool = True,
         members: Optional[str] = None) -> Dict[str, Any]:
    '''One artifact, as §21 publishes it.'''
    return {
        "id": row["id"],
        "step": row["step"],
        "index": row["index"],
        "kind": row["kind"],
        "media_type": row["media_type"],
        "size_bytes": row["size_bytes"],
        "digest": row["content_hash"],
        "created_at": row["created_at"],
        # Kept at least until then; null means no scheduled expiry, which is
        # what a legal hold is.
        "retained_until": None if row["legal_hold_at"] else row["retention_until"],
        # non-null means the bytes are gone and the row is not.
        "deleted_at": row["deleted_at"],
        # 🔴 **Two members, because they are two kinds of thing.** Without
        # either, `deleted_at` cannot be read: retention lapsing ends in one
        # like everything else -- it has to, because `fetchable`'s first
        # question is whether the bytes are there -- so the column alone cannot
        # tell *the system did what it said it would* from *somebody removed
        # this*.
        #
        # `deleted_cause` is a CLOSED enum and is what a client branches on.
        # `delete_reason` is prose and is what a person reads; it is named for
        # the column it comes from, because it is the same thing.
        "deleted_cause": cause(row),
        "delete_reason": row["delete_reason"],
        "fetchable": fetchable(row, surface_allows, members),
        # This profile takes no access requests, so there is never an
        # undecided one to name -- but the member is REQUIRED (surface D177).
        "access_requested_at": None,
    }
    # No `blocked_by` and no `access_request_url`: both are about an agreement
    # standing in the way, and this deployment has no agreements. An
    # unauthenticated deployment never emits access_request_url, because an
    # endpoint that always refuses is worse than an absent one.
