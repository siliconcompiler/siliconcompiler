'''
What a run left behind, as artifact rows the client lists and fetches.

Every artifact is stored gzipped, and only the kinds the client takes to rebuild
its build directory are made:

``manifest``  the job's ``<design>.pkg.json`` (job-level), and each node's own
``logs``      SiliconCompiler's ``job.log`` (job-level), and each node's log
              files as a tar
``node``      one node's whole working directory as a tar, ``inputs/`` included,
              relative to that directory

Each is made once, from the job's tree, read through :mod:`confine`.
'''

import gzip
import logging
import shutil
import tarfile
import time
import uuid

from pathlib import Path
from typing import Any, Dict, Optional

from siliconcompiler.remote.server.outputs import confine
from siliconcompiler.remote.server.state.store import iso
from siliconcompiler.utils import file_digest

__all__ = ["collect", "log_artifact", "wire"]


logger = logging.getLogger("sc-server")


def collect(store, directory: Path, tree: Path, job, nodes, final: bool) -> None:
    '''Make the artifacts ``tree`` has not yet got: for each of ``nodes`` that is
    done, and with ``final`` the job's own. Idempotent; the caller serializes it.'''
    design = job["design"]
    if final:
        _make(store, directory, job, "manifest", None, None,
              _gzipped(tree / f"{design}.pkg.json", tree))
        _make(store, directory, job, "logs", None, None, _gzipped(tree / "job.log", tree))

    for step, index in nodes:
        workdir = tree / step / index
        logs = sorted(path.name for path in _listdir(workdir) if path.name.endswith(".log"))
        _make(store, directory, job, "manifest", step, index,
              _gzipped(workdir / "outputs" / f"{design}.pkg.json", tree))
        _make(store, directory, job, "logs", step, index,
              _tarred(lambda tar: [confine.add_file(tar, tree, workdir / name, name)
                                   for name in logs]))
        _make(store, directory, job, "node", step, index,
              _tarred(lambda tar: confine.add_tree(tar, tree, workdir)))


def _listdir(path: Path):
    try:
        return list(path.iterdir())
    except OSError:
        return []


def _gzipped(path: Path, tree: Path):
    def write(target: Path) -> None:
        with confine.open_inside(tree, path) as source, gzip.open(target, "wb") as out:
            shutil.copyfileobj(source, out)
    return write


def _tarred(fill):
    def write(target: Path) -> None:
        with tarfile.open(target, "w:gz") as tar:
            fill(tar)
            if not tar.getmembers():
                raise FileNotFoundError("nothing to archive")
    return write


def _make(store, directory: Path, job, kind: str, step: Optional[str], index: Optional[str],
          write) -> None:
    '''Store one artifact, unless it exists or its source is not there to read.'''
    if store.one("SELECT 1 FROM artifacts WHERE job_id = ? AND kind = ? AND step IS ? "
                 "AND idx IS ?", (job["id"], kind, step, index)):
        return

    directory.mkdir(parents=True, exist_ok=True)
    artifact_id = str(uuid.uuid4())
    target = directory / artifact_id
    try:
        write(target)
    except OSError as e:
        target.unlink(missing_ok=True)
        if not isinstance(e, FileNotFoundError):
            logger.warning(f"{job['id']}: not keeping {kind} for {step}/{index}: {e}")
        return

    store.execute(
        "INSERT INTO artifacts (id, job_id, kind, step, idx, size_bytes, digest, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (artifact_id, job["id"], kind, step, index, target.stat().st_size,
         f"sha256:{file_digest(target).hexdigest()}", time.time()))


def log_artifact(store, job_id: str, step: str, index: str) -> Optional[str]:
    '''The id of a node's `logs` artifact, or None.'''
    row = store.one("SELECT id FROM artifacts WHERE job_id = ? AND kind = 'logs' "
                    "AND step = ? AND idx = ?", (job_id, step, index))
    return row["id"] if row else None


def wire(row) -> Dict[str, Any]:
    '''One artifact, as the listing publishes it.'''
    return {
        "id": row["id"], "step": row["step"], "index": row["idx"], "kind": row["kind"],
        "media_type": "application/gzip", "size_bytes": row["size_bytes"],
        "digest": row["digest"], "created_at": iso(row["created_at"]),
        "retained_until": None, "deleted_at": None, "deleted_cause": None,
        "deleted_reason": None, "fetchable": True, "access_requested_at": None,
        "can_request_access": False,
    }
