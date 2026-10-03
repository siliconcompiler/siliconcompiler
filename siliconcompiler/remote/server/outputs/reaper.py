'''Taking back the disk, once, at startup.

Bundles, expired artifacts' bytes, build trees and stale uploads go in that
order, each making the next cheaper to decide. 🔴 Without this a rig fills its
disk fast: every rebuild leaves a multi-gigabyte bundle (`images.sweep_bundles`).

⚠️ At startup and nowhere else, deliberately: never a surprise inside a request,
and a long-running deployment wants a real scheduled job. 🔴 Never fatal: a
server that will not start is worse than a full disk.
'''

import logging
import shutil

from pathlib import Path
from typing import Any, Dict

from siliconcompiler.remote.server.software import images
from siliconcompiler.remote.server.state.store import PENDING_STATES, TERMINAL_STATES, now

__all__ = ["sweep"]


logger = logging.getLogger("sc-server")

# Bound into the reaper's SQL as parameters.
_TERMINAL = tuple(sorted(TERMINAL_STATES))
_PENDING = f"state IN ({', '.join('?' * len(PENDING_STATES))})"


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
            logger.warning(f"could not reclaim {name}: {e}")
            taken[name] = 0

    # ⚠️ `abandoned` counts jobs, not bytes.
    freed = sum(value for name, value in taken.items() if name != "abandoned")
    if freed:
        from siliconcompiler.utils.units import format_binary

        def size(value) -> str:
            return format_binary(value, "B", digits=1, show_unit=True, compact=True,
                                 default="—")

        units = {"bundles": "container bundles", "artifacts": "expired artifacts",
                 "builds": "build directories", "uploads": "abandoned uploads"}
        logger.info(f"reclaimed {size(freed)}: " + ", ".join(
            f"{units[name]} {size(value)}"
            for name, value in taken.items()
            if value and name != "abandoned"))
    return taken


def _bundles(store, storage, config, datadir) -> int:
    if not config["containers"]:
        return 0
    return images.sweep_bundles(datadir / "images", store)


def _artifacts(store, storage, config, datadir) -> int:
    '''Reclaim bytes past their retention; the row stays.

    🔴 `deleted_at` is set: retention passing is not a ladder row, so without it
    a reaped artifact reports `fetchable: true`. ✅ `deleted_by` stays NULL, which
    reads as `deleted_cause: "expired"` (surface §21). A legal hold is skipped.
    '''
    from siliconcompiler.remote.server.outputs.artifacts import referenced_elsewhere

    rows = store.all(
        "SELECT id, location_id, storage_key, size_bytes FROM artifacts "
        "WHERE deleted_at IS NULL AND legal_hold_at IS NULL "
        "  AND retained_until IS NOT NULL AND retained_until <= ?", (now(),))

    freed = 0
    gone = 0
    for row in rows:
        try:
            path = storage.artifact_path(row["storage_key"])
            # Another live row's bytes too: its row goes, the object stays.
            if referenced_elsewhere(store, row):
                pass
            elif path.is_file():
                freed += path.stat().st_size
                path.unlink()
        except OSError as e:
            logger.debug(f"could not unlink {row['storage_key']}: {e}")
            continue

        # 🔴 Recorded whether or not a file was there to unlink.
        store.execute(
            "UPDATE artifacts SET deleted_at = ? WHERE id = ?", (now(), row["id"]))
        gone += 1

    if gone:
        logger.info(f"{gone} aged-out artifact(s) reclaimed")
    return freed


def _builds(store, storage, config, datadir) -> int:
    '''Reclaim a finished job's working tree, once nothing it produced is left.

    🔴 After the artifacts, which are indexed from it. ⚠️ A job with no
    artifacts is left alone: its indexing failed, and this is the only copy.
    Uploads, `staging` and `diagnostics` are not read from the tree, so they
    count on neither side.
    '''
    produced = ("NOT (a.kind = 'input' AND a.step IS NULL) "
                "AND a.kind NOT IN ('staging', 'diagnostics')")
    rows = store.all(
        "SELECT j.id, j.user_id FROM jobs j "
        f"WHERE j.state IN ({', '.join('?' * len(_TERMINAL))}) "
        "  AND j.deleted_at IS NULL "
        f"  AND EXISTS (SELECT 1 FROM artifacts a WHERE a.job_id = j.id AND {produced}) "
        "  AND NOT EXISTS (SELECT 1 FROM artifacts a WHERE a.job_id = j.id "
        f"                  AND {produced} AND a.deleted_at IS NULL "
        "                  AND (a.retained_until IS NULL "
        "                       OR a.retained_until > ?))",
        _TERMINAL + (now(),))

    freed = 0
    for row in rows:
        # 🔴 Impossible, and checked anyway: an empty id would `rmtree`
        # `<datadir>/users//builds/`, every user's work.
        if not row["user_id"] or not row["id"]:
            logger.warning("skipping a build directory with an empty id")
            continue

        root = (datadir / "users" / row["user_id"] / "builds" / row["id"])
        if not root.is_dir() or datadir not in root.resolve().parents:
            continue

        freed += images._weigh(root)
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(datadir / "jobbundles" / row["id"], ignore_errors=True)
        logger.info(f"reclaimed the build directory of {row['id'][:8]}")

    return freed


def _uploads(store, storage, config, datadir) -> int:
    '''Reclaim an upload left behind by a job that ended without submitting it.

    🔴 Never at the grant's expiry: the grant bounds when an upload may start,
    and a job still waiting may yet be submitted.
    '''
    rows = store.all(
        f"SELECT id FROM jobs WHERE NOT {_PENDING} AND upload_grant_expires_at IS NOT NULL",
        PENDING_STATES)

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
    '''Abandon jobs whose upload never arrived; returns a count of jobs.

    🔴 `reconcile` settles a job on read, but a job stuck in `created` is the one
    nobody opens, and it holds a `pending_uploads` slot meanwhile.
    '''
    from siliconcompiler.remote.server.jobs import JobService

    # 🔴 Through the service, the one writer of state transitions and history.
    jobs = JobService(store, config, storage, None, datadir)

    moved = 0
    for row in store.all(f"SELECT * FROM jobs WHERE {_PENDING}", PENDING_STATES):
        if jobs.abandon_if_expired(row):
            moved += 1

    if moved:
        logger.info(f"{moved} job(s) were never uploaded to; abandoned")
    return moved
