'''Taking back the disk, once, at startup.

🔴 **Nothing here was reclaiming anything, and a rig fills its disk fast.**
Measured on one afternoon of rebuilds: 28 GB on the data volume, 25 of it
bundles nothing could run any more. Every `--build` produces a new image
digest, which supersedes the old registry row and leaves the old six-and-a-half
gigabyte unpacked bundle exactly where it was.

Four things accumulate, and they go in this order because each one makes the
next cheaper to decide:

``bundles``    an image unpacked onto the filesystem. The largest by far
``artifacts``  bytes whose ``retention_until`` has passed. The row stays --
               *where did my results go* has to stay answerable -- and records
               that retention was what took them
``builds``     a job's working tree, once nothing it produced is left. It is
               the source the artifacts were indexed FROM, so it may only go
               after them
``uploads``    a staged archive for a job that was created and never submitted,
               past the expiry its own grant was issued with

⚠️ **At startup and nowhere else, deliberately.** A background thread is
machinery this profile does not need: a demo rig is restarted constantly, and a
deployment that runs for months wants a real scheduled job rather than
something a web process does when it feels like it. What it must never be is a
surprise inside somebody's request, which is the other place it could have
gone.

🔴 **Never fatal.** A server that will not start because it could not delete
something is worse than a full disk, which at least says what it is.
'''

import logging
import shutil

from pathlib import Path
from typing import Any, Dict

from siliconcompiler.remote.server import images
from siliconcompiler.remote.server.store import now

__all__ = ["sweep"]


logger = logging.getLogger("sc-server")

# The five states a job can be in and never leave. Spelled out because the
# reaper reads them in SQL, where it cannot consult `job_states.terminal`.
_TERMINAL = ("completed", "failed", "cancelled", "rejected", "abandoned")


def sweep(store, storage, config, datadir) -> Dict[str, Any]:
    '''Reclaim what nothing can use. Returns what it took, for the log.'''
    datadir = Path(datadir)
    taken: Dict[str, Any] = {}

    for name, step in (("bundles", _bundles),
                       ("artifacts", _artifacts),
                       ("builds", _builds),
                       ("uploads", _uploads),
                       ("abandoned", _abandoned)):
        try:
            taken[name] = step(store, storage, config, datadir)
        except Exception as e:                                   # noqa: BLE001
            # One kind failing must not stop the others, and none of them may
            # stop the server.
            logger.warning(f"could not reclaim {name}: {e}")
            taken[name] = 0

    # ⚠️ `abandoned` counts jobs and the rest count bytes, so it is reported
    # on its own rather than summed into a figure that would then be wrong.
    freed = sum(value for name, value in taken.items() if name != "abandoned")
    if freed:
        from siliconcompiler.remote.units import size

        logger.info(f"reclaimed {size(freed)}: " + ", ".join(
            f"{units_of(name)} {size(value)}"
            for name, value in taken.items()
            if value and name != "abandoned"))
    return taken


def units_of(name: str) -> str:
    return {"bundles": "container bundles",
            "artifacts": "expired artifacts",
            "builds": "build directories",
            "uploads": "abandoned uploads",
            "abandoned": "abandoned jobs"}[name]


def _bundles(store, storage, config, datadir) -> int:
    if not config["containers"]:
        return 0
    return images.sweep_bundles(datadir / "images", store)


# What the reaper writes into `delete_reason`, and it is a constant because a
# client compares against it. `deleted_by` distinguishes the reaper from a
# person in the table -- NULL is the reaper -- but `deleted_by` is not on the
# wire and cannot be: it names a user to callers who may not know that user
# exists.
RETENTION_LAPSED = "retention lapsed"


def _artifacts(store, storage, config, datadir) -> int:
    '''Bytes past their retention. The row stays; only the bytes go.

    🔴 **`deleted_at` IS set, and the tempting alternative breaks the ladder.**
    Leaving the row untouched reads better -- the column means *the bytes are
    gone* and a client renders it "deleted on 24 Sep", which sounds like a
    person -- but `fetchable` is decided by an ordered ladder whose first row is
    `deleted_at`. `expires_at` passing is deliberately NOT a row on it, because
    retention lapsing is followed by this, and this is where it lands. Take the
    write away and a reaped artifact falls through to the entitlement rows and
    reports `fetchable: true` for bytes that are not there.

    ✅ **The real defect the alternative was aimed at is that a client could
    not tell an expiry from a deletion, and the fix is to say which.**
    `delete_reason` is written here and published as `deleted_reason`, so
    *aged out on 24 Sep* and *deleted on 24 Sep* are two different sentences
    again -- without `fetchable` having to lie for it.

    A legal hold is skipped. It is not only policy -- the table would refuse
    the write, since an artifact cannot be both held and deleted.
    '''
    rows = store.all(
        "SELECT id, storage_key, size_bytes FROM artifacts "
        "WHERE deleted_at IS NULL AND legal_hold_at IS NULL "
        "  AND retention_until IS NOT NULL AND retention_until <= ?", (now(),))

    freed = 0
    gone = 0
    for row in rows:
        try:
            path = storage.artifact_path(row["storage_key"])
            if path.is_file():
                freed += path.stat().st_size
                path.unlink()
        except OSError as e:
            logger.debug(f"could not unlink {row['storage_key']}: {e}")
            continue

        # 🔴 Recorded whether or not a file was there to unlink. The row is the
        # claim that these bytes are unavailable, and an artifact whose file
        # had already vanished is the case where that claim matters most.
        # `deleted_by` stays NULL, which is how the table says *the reaper*.
        store.execute(
            "UPDATE artifacts SET deleted_at = ?, delete_reason = ? WHERE id = ?",
            (now(), RETENTION_LAPSED, row["id"]))
        gone += 1

    if gone:
        logger.info(f"{gone} aged-out artifact(s) reclaimed")
    return freed


def _builds(store, storage, config, datadir) -> int:
    '''A finished job's working tree, once nothing it produced is left.

    🔴 After the artifacts and never before: this tree is what they were
    indexed FROM, and the portal reads a node's log straight out of it while it
    is there. Once every artifact of a job is gone the tree holds nothing that
    is still reachable, and it is the second largest thing on the disk.

    ⚠️ A job with no artifacts at all is left alone. That is a run whose
    indexing failed or has not happened, not a run whose results expired, and
    deleting the only copy of it is the one mistake here that cannot be undone.
    '''
    rows = store.all(
        "SELECT j.id, j.user_id FROM jobs j "
        f"WHERE j.state IN ({', '.join('?' * len(_TERMINAL))}) "
        "  AND j.deleted_at IS NULL "
        "  AND EXISTS (SELECT 1 FROM artifacts a WHERE a.job_id = j.id) "
        # Nothing this job produced is still reachable: every artifact is
        # either past its retention or was deleted outright.
        "  AND NOT EXISTS (SELECT 1 FROM artifacts a WHERE a.job_id = j.id "
        "                  AND a.deleted_at IS NULL "
        "                  AND (a.retention_until IS NULL "
        "                       OR a.retention_until > ?))",
        _TERMINAL + (now(),))

    freed = 0
    for row in rows:
        # 🔴 Insurance on the one operation here that cannot be undone. Both
        # ids are NOT NULL primary keys, so an empty one is impossible -- and
        # an empty one would make this path `<datadir>/users//builds/` and
        # `rmtree` every user's work. A condition that cannot happen is exactly
        # the one worth checking when being wrong costs that much.
        if not row["user_id"] or not row["id"]:
            logger.warning("skipping a build directory with an empty id")
            continue

        root = (datadir / "users" / row["user_id"] / "builds" / row["id"])
        if not root.is_dir() or datadir not in root.resolve().parents:
            continue

        freed += _weigh(root)
        shutil.rmtree(root, ignore_errors=True)
        logger.info(f"reclaimed the build directory of {row['id'][:8]}")

    return freed


def _uploads(store, storage, config, datadir) -> int:
    '''An archive uploaded for a job that was never submitted.

    `upload_grant_expires_at` is the trigger the schema names it for. A job
    still in `created` or `awaiting_input` past it will not be submitted --
    submit re-issues a grant rather than honouring a lapsed one -- so the bytes
    are only holding a slot against `limits.pending_uploads`.
    '''
    rows = store.all(
        "SELECT id FROM jobs WHERE state IN ('created', 'awaiting_input') "
        "  AND upload_grant_expires_at IS NOT NULL "
        "  AND upload_grant_expires_at <= ?", (now(),))

    freed = 0
    for row in rows:
        try:
            path = storage.upload_path(row["id"])
            if path.is_file():
                freed += path.stat().st_size
        except OSError:
            pass
        storage.discard_upload(row["id"])

    return freed


def _abandoned(store, storage, config, datadir) -> int:
    '''Jobs whose upload never arrived, settled at last.

    🔴 **A job settles when somebody looks at it, and this is for the ones
    nobody does.** `reconcile` abandons an expired job on read -- but a job
    stuck in `created` is exactly the job nobody opens, and while it sits there
    it holds a `pending_uploads` slot against its owner's allowance. That is
    the failure worth catching: the ceiling is reached by jobs that no longer
    exist in any meaningful sense.

    ⚠️ Returns a count and not bytes, which is why `sweep` reports it
    separately -- the number in the log is jobs, and nothing was freed on disk
    beyond whatever `_uploads` already took.
    '''
    from siliconcompiler.remote.server.jobs import JobService

    # 🔴 Through the service, not a second UPDATE here. One writer for a state
    # transition, or the two drift and only one of them writes the history row
    # that says why.
    jobs = JobService(store, config, storage, None, datadir)

    moved = 0
    for row in store.all(
            "SELECT * FROM jobs WHERE state IN ('created', 'awaiting_input')"):
        if jobs.abandon_if_expired(row):
            moved += 1

    if moved:
        logger.info(f"{moved} job(s) were never uploaded to; abandoned")
    return moved


def _weigh(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file() and not child.is_symlink():
                total += child.stat().st_size
        except OSError:
            continue
    return total
