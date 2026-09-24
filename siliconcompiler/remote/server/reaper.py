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
               *where did my results go* has to stay answerable -- and the
               bytes do not
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
                       ("uploads", _uploads)):
        try:
            taken[name] = step(store, storage, config, datadir)
        except Exception as e:                                   # noqa: BLE001
            # One kind failing must not stop the others, and none of them may
            # stop the server.
            logger.warning(f"could not reclaim {name}: {e}")
            taken[name] = 0

    freed = sum(taken.values())
    if freed:
        from siliconcompiler.remote.units import size

        logger.info(f"reclaimed {size(freed)}: " + ", ".join(
            f"{units_of(name)} {size(value)}"
            for name, value in taken.items() if value))
    return taken


def units_of(name: str) -> str:
    return {"bundles": "container bundles",
            "artifacts": "expired artifacts",
            "builds": "build directories",
            "uploads": "abandoned uploads"}[name]


def _bundles(store, storage, config, datadir) -> int:
    if not config["containers"]:
        return 0
    return images.sweep_bundles(datadir / "images", store)


def _artifacts(store, storage, config, datadir) -> int:
    '''Bytes past their retention. The row stays; only the bytes go.

    🔴 **`deleted_at` is deliberately NOT set, and that is the opposite of what
    it looks like.** The column means *somebody decided*, and a client renders
    it as exactly that -- "deleted on 24 Sep" -- ahead of every other reason,
    because [saying a thing expired when a person removed it] is the one wrong
    answer that matters. Retention lapsing is the system doing what it said it
    would, and `expires_at` in the past already says so. Setting `deleted_at`
    here would have turned every aged-out object into a report that somebody
    took it.

    ⚠️ **So nothing in the row distinguishes *expired, bytes still on disk*
    from *expired, bytes reclaimed*, and nothing needs to:** `fetchable` is
    false either way and no caller can have them either way. The distinction
    would only matter to an operator, who has the filesystem.

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
                gone += 1
        except OSError as e:
            logger.debug(f"could not unlink {row['storage_key']}: {e}")

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


def _weigh(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file() and not child.is_symlink():
                total += child.stat().st_size
        except OSError:
            continue
    return total
