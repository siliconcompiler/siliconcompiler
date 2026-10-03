'''
The server's own record of a job, kept apart from the run's `logs`.

``staging``      for the submitter: what this server did from create to
                 dispatch, a section per staging pass, every line scrubbed like
                 `detail`
``diagnostics``  for the operators, not scrubbed: named files in one tar, never
                 handed over the API. A new sort of record is a new file name,
                 never a new kind

Both live in the job root, above the tree an upload expands into, so nothing a
job uploads or runs can write them.
'''

import logging

from pathlib import Path
from typing import Iterable, Optional

from siliconcompiler.remote.server.errors import bound
from siliconcompiler.remote.server.state.store import now

__all__ = ["STAGING_LOG", "DIAGNOSTICS_DIR", "begin_pass", "note", "keep",
           "diagnostics_files"]


logger = logging.getLogger("sc-server")


STAGING_LOG = "sc-server-staging.log"

# Job-level files at its top, a node's under ``<step>/<index>/``.
DIAGNOSTICS_DIR = "sc-server-diagnostics"


def begin_pass(job_root) -> None:
    '''Start a new section of the `staging` record for this staging pass.'''
    root = Path(job_root)
    passes = 0
    try:
        with open(root / STAGING_LOG) as f:
            passes = sum(1 for line in f if line.startswith("==> staging, pass "))
    except OSError:
        pass
    _append(root, [f"==> staging, pass {passes + 1}, from {now()} <=="], stamp=False)


def note(job_root, lines: Iterable[str]) -> None:
    '''Append lines to the `staging` record, each scrubbed and bounded like `detail`.'''
    _append(Path(job_root), [bound(str(line)) for line in lines])


def keep(job_root, name: str, text: str, step: Optional[str] = None,
         index: Optional[str] = None) -> None:
    '''Append to one named `diagnostics` file, the job's or a node's.'''
    where = Path(job_root) / DIAGNOSTICS_DIR
    if step is not None:
        where = where / step / index
    try:
        where.mkdir(parents=True, exist_ok=True)
        with open(where / name, "a", errors="replace") as f:
            f.write(text if text.endswith("\n") else f"{text}\n")
    except OSError as e:
        logger.warning(f"could not keep {name} for the operators: {e}")


def diagnostics_files(job_root, step: Optional[str] = None,
                      index: Optional[str] = None):
    '''``(name, path)`` pairs `diagnostics` holds for the job or one node.'''
    from siliconcompiler.remote.server.running.dispatch import RUN_LOG

    root = Path(job_root)
    where = root / DIAGNOSTICS_DIR
    if step is not None:
        where = where / step / index
    found = []
    if where.is_dir() and not where.is_symlink():
        found = [(child.name, child) for child in sorted(where.iterdir())
                 if child.is_file() and not child.is_symlink()]
    if step is None:
        run_log = root / RUN_LOG
        if run_log.is_file() and not run_log.is_symlink():
            found.append(("run.log", run_log))
    return found


def _append(root: Path, lines, stamp: bool = True) -> None:
    try:
        root.mkdir(parents=True, exist_ok=True)
        with open(root / STAGING_LOG, "a") as f:
            for line in lines:
                f.write(f"{now()} {line}\n" if stamp else f"{line}\n")
    except OSError as e:
        logger.warning(f"could not write the job's staging record: {e}")
