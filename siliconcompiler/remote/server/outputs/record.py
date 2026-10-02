'''
The server's own record of a job, kept apart from the run's (surface D295).

Two records, for two readers, and neither is ever inside the run's `logs`:

``staging``      for the person who submitted the job: what this server did
                 from create to dispatch -- what it fetched and could not, what
                 the manifest's read found, each Python package it installed or
                 substituted and each it sent the job back for, with why, and
                 each image it pulled. A section each time the job stages, and
                 every line scrubbed like `detail`, since everyone who can read
                 the job reads it.
``diagnostics``  for the deployment's operators, and not scrubbed: named files
                 in one tar -- the builder's own output (``builder.log``), the
                 runner's (``run.log``), and the scheduler's view of the job
                 and of each node (``slurm.txt``). A new sort of record is a new
                 file name here, never a new kind. Never handed over the API.

Both live in the job root, beside the progress file and above the tree an
upload expands into, so nothing a job uploads or runs can write them.
'''

import logging

from pathlib import Path
from typing import Iterable, Optional

from siliconcompiler.remote.server.errors import bound
from siliconcompiler.remote.server.state.store import now

__all__ = ["STAGING_LOG", "DIAGNOSTICS_DIR", "begin_pass", "note", "keep",
           "diagnostics_files"]


logger = logging.getLogger("sc-server")


# The job's `staging` record, as it is written.
STAGING_LOG = "sc-server-staging.log"

# The files `diagnostics` packs: job-level at its top, a node's under
# ``<step>/<index>/``.
DIAGNOSTICS_DIR = "sc-server-diagnostics"


def begin_pass(job_root) -> None:
    '''A new section of the `staging` record: this pass of staging starts.'''
    root = Path(job_root)
    passes = 0
    try:
        with open(root / STAGING_LOG) as f:
            passes = sum(1 for line in f if line.startswith("==> staging, pass "))
    except OSError:
        pass
    _append(root, [f"==> staging, pass {passes + 1}, from {now()} <=="], stamp=False)


def note(job_root, lines: Iterable[str]) -> None:
    '''Lines of the `staging` record, each scrubbed and bounded like
    `detail`.'''
    _append(Path(job_root), [bound(str(line)) for line in lines])


def keep(job_root, name: str, text: str, step: Optional[str] = None,
         index: Optional[str] = None) -> None:
    '''One named file of `diagnostics`: the job's, or a node's. Appended to,
    since a job may stage more than once, and kept as it was written.'''
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
    '''What `diagnostics` holds for the job, or for one node: ``(name, path)``
    pairs, the runner's own log among the job's.'''
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
