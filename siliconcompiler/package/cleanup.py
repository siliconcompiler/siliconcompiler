# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
"""
Collection of stale entries from the on-disk data source cache.

The data source cache in ``~/.sc/cache/dataroot`` (or
``[option,cachedir]/dataroot``) only ever grows: every new version of a data
source lands beside the old ones, and nothing removes an entry once the design
that needed it has moved on. This module is the garbage collector for that
directory, used both by the ``cleanup`` support app and by the automatic sweep
at the start of every run (:func:`auto_cleanup`).

Only the data source area is collected. The tool cache
(:func:`~siliconcompiler.utils.paths.toolcachedir`, the cache's other
subdirectory) is deliberately left alone: a tool that keeps a cache between runs
caps it itself -- ccache has ``max_size`` -- and a sweep here that judged it by
lock files would collect nothing, since a tool writes no lock file. That is a
decision, not an oversight: if a tool is ever added that grows without bound,
the answer is a sweep that knows that tool's layout, not this one.

Entries left by releases before the cache was split into subdirectories sit
loose in the cache root. They are collected here too, on the same clock, so that
the split does not strand them where nothing will ever look again. Nothing is
migrated: an entry that is still wanted is re-downloaded into ``dataroot/`` the
next time it resolves, which costs a download and no data.

That legacy pass is dead code the day nobody upgrades across the split any more.
It is scheduled for removal after **2027-09-09**, a year of releases on: by then
an install that has run once has had its loose entries collected on the ordinary
90-day clock, and one that has not run in a year is not being upgraded either.
Delete the root half of :func:`cleanup_cache` and the two area names it reads
back: sweeping ``dataroot/`` needs neither, since everything in it is an entry.

Two kinds of residue are collected:

* **Entries** -- a cached directory plus its lock files, judged by the lock
  file's modification time, which :meth:`RemoteResolver._touch_lock` stamps on
  every resolve.
* **Orphaned lock files** -- a ``.lock`` or ``.sc_lock`` whose directory is
  already gone. They are empty, but nothing else can ever collect them, so they
  accumulate for the life of the install. These are collected on sight rather
  than on the age threshold: a lock with nothing to guard is residue, and one is
  free to recreate. Only a lock new enough to belong to a download still
  creating its directory is spared.
"""

import contextlib
import logging
import os
import shutil
import stat

import os.path

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Union

from fasteners import InterProcessLock

from siliconcompiler.package import RemoteResolver
from siliconcompiler.utils.multiprocessing import MPManager
from siliconcompiler.utils.paths import cachedir as cachedir_path, \
    datarootdir, toolcachedir


#: Settings category (in ``~/.sc/settings.json``) holding the automatic sweep's knobs.
SETTINGS_CATEGORY = "cache"

#: Days an entry must go unused before it is collected, by the automatic sweep and
#: by the ``cleanup`` app alike.
DEFAULT_DAYS = 90

#: Minimum days between two automatic sweeps of the same cache directory. The
#: automatic sweep is unasked-for housekeeping, so it stays out of the way.
DEFAULT_INTERVAL = 7

#: Records when a cache directory was last swept automatically.
STAMP_FILE = ".sc_cleanup"

#: Suffixes of the lock files that sit beside a cache entry.
LOCK_SUFFIXES = (".lock", ".sc_lock")

#: How recently a lock must have been taken to belong, plausibly, to a running
#: process -- one still downloading behind the fallback lock, or one that has not
#: created its cache directory yet. RemoteResolver gives up waiting on a lock
#: after 10 minutes, so one older than this is residue.
LOCK_ACTIVE_SECONDS = 60 * 60


@dataclass
class CleanupStats:
    """
    Tally of what a sweep removed.

    Attributes:
        entries (int): Cache entry directories removed.
        locks (int): Orphaned lock files removed.
        size (int): Total bytes freed by the removed entries.
        errors (int): Failures encountered; the sweep continues past all of them.
    """
    entries: int = 0
    locks: int = 0
    size: int = 0
    errors: int = 0


def format_size(size_bytes: float) -> str:
    """
    Formats a byte count into a human-readable size string.

    Args:
        size_bytes (float): The number of bytes.

    Returns:
        str: The size with a unit suffix, e.g. ``"1.5MB"``.
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def _entry_lock_mtime(cachedir: Path, name: str) -> Optional[float]:
    """
    Reads when a cache entry's lock was last stamped.

    Args:
        cachedir (Path): The cache directory holding the entry.
        name (str): The entry's directory name.

    Returns:
        float: The lock file's modification time, or None if the entry has no
            lock file and so no access record at all.

    Raises:
        OSError: If a lock file is there but cannot be read.
    """
    for suffix in LOCK_SUFFIXES:
        try:
            return (cachedir / f"{name}{suffix}").stat().st_mtime
        except FileNotFoundError:
            continue
    return None


@contextlib.contextmanager
def _exclusive(cachedir: Path, name: str):
    """
    Holds a cache entry's download lock for the duration of its removal.

    A sweep can run while other SiliconCompiler processes are resolving data
    sources, so an entry must not be deleted out from under a reader. This takes
    the same lock :meth:`RemoteResolver.resolve` holds while downloading, without
    waiting: a busy entry is left for the next sweep rather than blocking the run.

    Args:
        cachedir (Path): The cache directory holding the entry.
        name (str): The entry's directory name.

    Yields:
        bool: True if the caller now holds the lock and may delete, False if
            another process is working on the entry.
    """
    # The fallback lock exists only while it is held -- RemoteResolver unlinks it
    # on release -- so a recent one means a live download on a filesystem where
    # flock is unavailable, which is also the case the file lock below cannot
    # detect. An old one is residue from a process that was killed.
    fallback = cachedir / f"{name}.sc_lock"
    try:
        if os.path.exists(fallback) and \
                datetime.now().timestamp() - fallback.stat().st_mtime < LOCK_ACTIVE_SECONDS:
            yield False
            return
    except OSError:
        yield False
        return

    primary = cachedir / f"{name}.lock"
    if not os.path.exists(primary):
        # Nothing to take a lock on, and creating one here would leave behind the
        # very orphan this module collects.
        yield True
        return

    lock = InterProcessLock(str(primary))
    try:
        acquired = lock.acquire(blocking=False)
    except (OSError, RuntimeError):
        # Filesystem does not support locking; resolve() falls back to the
        # existence check already made above.
        yield True
        return

    try:
        yield acquired
    finally:
        if acquired:
            # Bookkeeping on an open descriptor; failing at it must not abort
            # the rest of the sweep.
            with contextlib.suppress(Exception):
                lock.release()


def _remove_locks(cachedir: Path, name: str, logger: logging.Logger) -> None:
    """
    Deletes both of a cache entry's lock files, if they exist.

    Args:
        cachedir (Path): The cache directory holding the entry.
        name (str): The entry's directory name.
        logger (logging.Logger): Logger for reporting what could not be removed.
    """
    for suffix in LOCK_SUFFIXES:
        lock_file = cachedir / f"{name}{suffix}"
        try:
            lock_file.unlink(missing_ok=True)
        except OSError as e:
            # The entry itself is gone, so this is now an orphan and a later
            # sweep will try again.
            logger.warning(f"Could not remove {lock_file.name}: {e}")


def _directory_size(path: Path, logger: logging.Logger) -> int:
    """
    Sums the size of every file under a directory.

    Args:
        path (Path): The directory to measure.
        logger (logging.Logger): Logger for reporting unreadable entries.

    Returns:
        int: The total size in bytes, 0 if the directory could not be walked.
    """
    try:
        return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
    except OSError as e:
        logger.warning(f"Could not calculate size for {path.name}: {e}")
        return 0


def _collect_entries(cachedir: Path,
                     cutoff: float,
                     dryrun: bool,
                     logger: logging.Logger,
                     stats: CleanupStats,
                     skip: Tuple[str, ...] = ()) -> None:
    """
    Removes cache entry directories that have gone unused, and their lock files.

    An entry with no lock file at all is left alone: there is no access record
    for it, so there is nothing to judge it by.

    Args:
        cachedir (Path): The cache directory to sweep.
        cutoff (float): Timestamp before which an entry counts as unused.
        dryrun (bool): Report what would be removed without removing it.
        logger (logging.Logger): Logger for progress and errors.
        stats (CleanupStats): Tally to add this pass's removals to.
        skip (tuple of str): Names in this directory that are not entries and
            must be left alone, whatever their age.
    """
    for entry in sorted(cachedir.iterdir()):
        if not os.path.isdir(entry):
            continue

        if entry.name in skip:
            continue

        try:
            lock_mtime = _entry_lock_mtime(cachedir, entry.name)
        except OSError as e:
            logger.warning(f"Could not stat lock file for {entry.name}: {e}")
            stats.errors += 1
            continue

        if lock_mtime is None:
            logger.debug(f"No lock file found for {entry.name}, skipping")
            continue

        if lock_mtime >= cutoff:
            continue

        size = _directory_size(entry, logger)
        last_accessed = datetime.fromtimestamp(lock_mtime)
        message = (f"Removing {entry.name} "
                   f"(last accessed: {last_accessed.isoformat()}, "
                   f"size: {format_size(size)})")

        if dryrun:
            logger.info(message)
            stats.entries += 1
            stats.size += size
            continue

        removed = False
        with _exclusive(cachedir, entry.name) as exclusive:
            if not exclusive:
                logger.info(f"Skipping {entry.name}, it is in use by another process")
                continue

            logger.info(message)
            try:
                # Cache entries are made read-only after download
                RemoteResolver._make_writable(entry)
                shutil.rmtree(entry)
                removed = True
            except Exception as e:
                logger.error(f"Failed to delete {entry.name}: {e}")
                stats.errors += 1

        if not removed:
            continue

        # Outside the lock: Windows refuses to unlink a file another handle
        # still holds open, and the handle in question is the one just released.
        _remove_locks(cachedir, entry.name, logger)

        stats.entries += 1
        stats.size += size


def _collect_orphan_locks(cachedir: Path,
                          dryrun: bool,
                          logger: logging.Logger,
                          stats: CleanupStats) -> None:
    """
    Removes lock files whose cache entry is already gone.

    :func:`_collect_entries` only visits directories, so these are invisible to
    it and nothing else in SiliconCompiler ever removes one. They are not judged
    on age: an empty file guarding a directory that does not exist is residue
    whenever it was written, and a lock costs nothing to recreate. The one
    exception is a lock taken within :data:`LOCK_ACTIVE_SECONDS`, which may
    belong to a download that has not created its directory yet.

    Args:
        cachedir (Path): The cache directory to sweep.
        dryrun (bool): Report what would be removed without removing it.
        logger (logging.Logger): Logger for progress and errors.
        stats (CleanupStats): Tally to add this pass's removals to.
    """
    cutoff = datetime.now().timestamp() - LOCK_ACTIVE_SECONDS

    for lock_file in sorted(cachedir.iterdir()):
        suffix = lock_file.suffix
        if suffix not in LOCK_SUFFIXES:
            continue

        name = lock_file.name[:-len(suffix)]
        if os.path.exists(cachedir / name):
            continue

        try:
            info = lock_file.stat()
        except FileNotFoundError:
            # Removed under us, which is the outcome this pass wanted anyway
            continue
        except OSError as e:
            logger.warning(f"Could not stat lock file {lock_file}: {e}")
            stats.errors += 1
            continue

        if not stat.S_ISREG(info.st_mode):
            # Something that merely ends in .lock
            continue

        lock_mtime = info.st_mtime
        if lock_mtime >= cutoff:
            logger.debug(f"{lock_file.name} was taken too recently to be residue, skipping")
            continue

        last_taken = datetime.fromtimestamp(lock_mtime)
        message = (f"Removing orphaned lock {lock_file.name} "
                   f"(last taken: {last_taken.isoformat()})")

        if dryrun:
            logger.info(message)
            stats.locks += 1
            continue

        with _exclusive(cachedir, name) as exclusive:
            if not exclusive:
                logger.info(f"Skipping {lock_file.name}, it is in use by another process")
                continue

        # Taking the lock proved nobody else is using it; unlinking happens once
        # it is released, so Windows still has no open handle to refuse.
        logger.info(message)
        try:
            lock_file.unlink(missing_ok=True)
            stats.locks += 1
        except OSError as e:
            logger.error(f"Failed to delete {lock_file.name}: {e}")
            stats.errors += 1


def cleanup_cache(cachedir: Union[str, Path],
                  days: int,
                  dryrun: bool = False,
                  logger: Optional[logging.Logger] = None,
                  collect_entries: bool = True) -> CleanupStats:
    """
    Removes cache entries and orphaned lock files that have gone unused.

    An entry is collected when the modification time of its lock file -- stamped
    on every resolve by :meth:`RemoteResolver._touch_lock` -- is older than
    ``days``. A ``.lock`` or ``.sc_lock`` whose entry directory is already gone
    is collected regardless of ``days``, unless it was stamped within the last
    :data:`LOCK_ACTIVE_SECONDS`, which may mean a resolve is holding it and has
    not created its directory yet. See :func:`_collect_entries` and
    :func:`_collect_orphan_locks`.

    Two directories are swept: the data source area,
    :func:`~siliconcompiler.utils.paths.datarootdir`, and the cache root itself,
    where releases before the split left their entries. The tool cache is stepped
    over -- see this module's own documentation for why nothing collects it.

    Deleting a cache entry is not destructive; it is re-downloaded the next time
    it is resolved.

    Args:
        cachedir (Path): The cache directory to sweep. This is the root of the
            cache, not the data source area inside it.
        days (int): Remove entries not accessed in this many days.
        dryrun (bool): Report what would be removed without removing it.
        logger (logging.Logger): Logger for progress and errors.
        collect_entries (bool): Whether to collect entry directories at all. Pass
            False to sweep only the orphaned lock files, which need no access
            history to judge.

    Returns:
        CleanupStats: What was removed, totalled over both areas.
    """
    if logger is None:
        logger = logging.getLogger("siliconcompiler")

    cachedir = Path(cachedir)
    stats = CleanupStats()
    cutoff = (datetime.now() - timedelta(days=days)).timestamp()

    # Both subdirectory names are read back from the path functions rather than
    # spelled here: one that drifted from the name the resolvers write to would
    # turn stepping over a live area into deleting it.
    default_root = cachedir_path(None)
    dataroot = os.path.relpath(datarootdir(None), default_root)
    toolcache = os.path.relpath(toolcachedir(None), default_root)

    # The root is swept last: an entry there is residue from before the cache was
    # split, so the area that is actually in use is the one worth reporting on
    # first. Both subdirectories are stepped over on that pass -- each is an area
    # in its own right, not an entry an older release left loose. That pass is
    # temporary; see this module's documentation for when it goes.
    areas = (
        (cachedir / dataroot, ()),
        (cachedir, (dataroot, toolcache))
    )

    for area, skip in areas:
        if not os.path.isdir(area):
            continue

        if collect_entries:
            _collect_entries(area, cutoff, dryrun, logger, stats, skip=skip)

        _collect_orphan_locks(area, dryrun, logger, stats)

    return stats


def auto_cleanup(project) -> None:
    """
    Sweeps the data source cache at the start of a run.

    This is the only thing that runs :func:`cleanup_cache` without being asked,
    so it is deliberately timid. It is throttled to one sweep per cache directory
    per ``cleanupinterval`` days (weekly by default), it only collects what has
    gone unused for ``cleanupdays`` (90 by default), and every failure is
    swallowed -- a housekeeping pass must never be the reason a run does not
    start.

    Both knobs live in the ``cache`` category of ``~/.sc/settings.json``, so a
    user or a site administrator can tune or disable the sweep:

    .. code-block:: json

        {"cache": {"cleanupdays": 30, "cleanupinterval": 1}}

    Setting ``cleanupdays`` to 0 turns the automatic sweep off entirely.

    Args:
        project (Project): The project whose cache directory should be swept.
    """
    logger = project.logger.getChild("cache")

    try:
        settings = MPManager.get_settings()
        try:
            days = int(settings.get(SETTINGS_CATEGORY, "cleanupdays",
                                    default=DEFAULT_DAYS))
            interval = int(settings.get(SETTINGS_CATEGORY, "cleanupinterval",
                                        default=DEFAULT_INTERVAL))
        except (TypeError, ValueError):
            logger.warning("Invalid cache cleanup settings, using defaults")
            days, interval = DEFAULT_DAYS, DEFAULT_INTERVAL

        if days <= 0:
            return

        cachedir = Path(cachedir_path(project))
        if not os.path.isdir(cachedir):
            # Nothing has been cached yet
            return

        stamp = cachedir / STAMP_FILE
        first_sweep = not os.path.exists(stamp)
        if not first_sweep:
            age = datetime.now().timestamp() - stamp.stat().st_mtime
            if age < timedelta(days=max(interval, 0)).total_seconds():
                return

        try:
            stamp.touch()
        except OSError as e:
            # A cache directory that cannot be stamped cannot be throttled, and
            # sweeping it on every single run is worse than not sweeping it.
            logger.debug(f"Could not record cache cleanup time in {stamp}: {e}")
            return

        if first_sweep:
            # Until this release the lock file's mtime was the download time, not
            # the access time, so every entry on an existing install looks as old
            # as the day it was fetched -- including the ones in use every day.
            # Spare them all: this run's own resolves stamp everything it still
            # needs, and the next sweep sees real access times. The orphaned
            # locks are collected now regardless; judging those needs no history.
            logger.debug(f"Recording baseline cache access times in {cachedir}")

        stats = cleanup_cache(cachedir, days, logger=logger,
                              collect_entries=not first_sweep)

        if stats.entries:
            logger.info(f"Cleaned up {stats.entries} cache "
                        f"{'entry' if stats.entries == 1 else 'entries'} "
                        f"({format_size(stats.size)}) "
                        f"not used in {days} days")
        if stats.locks:
            logger.info(f"Cleaned up {stats.locks} orphaned lock "
                        f"{'file' if stats.locks == 1 else 'files'}")
    except Exception as e:
        # Housekeeping is never worth failing a run over.
        logger.debug(f"Cache cleanup skipped: {e} ({e.__class__.__name__})")
