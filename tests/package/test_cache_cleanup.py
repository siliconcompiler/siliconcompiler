# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
import logging
import os
import pytest

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from siliconcompiler import Project
from siliconcompiler.package import cleanup
from siliconcompiler.utils.multiprocessing import MPManager


@pytest.fixture
def cachedir():
    '''An empty cache directory in the test's own working directory.'''
    path = Path("cache")
    path.mkdir()
    return path


@pytest.fixture
def project(project_logger):
    proj = Project("testproj")
    project_logger(proj)
    proj.logger.setLevel(logging.INFO)
    proj.option.set_cachedir("cache")
    return proj


def make_entry(cachedir, name, age_days=None, lock=".lock", contents=b"data"):
    '''Create a cache entry directory and its lock file, aged by age_days.'''
    entry = cachedir / name
    entry.mkdir()
    (entry / "data.txt").write_bytes(contents)

    if lock is None:
        return entry

    lock_file = cachedir / f"{name}{lock}"
    lock_file.touch()
    if age_days is not None:
        age_lock(lock_file, age_days)

    return entry


def age_lock(lock_file, age_days):
    '''Backdate a lock file by age_days days.'''
    when = (datetime.now() - timedelta(days=age_days)).timestamp()
    os.utime(lock_file, (when, when))


# ============================================================================
# format_size
# ============================================================================

def test_format_size_bytes():
    assert cleanup.format_size(512) == "512.0B"


def test_format_size_kilobytes():
    assert cleanup.format_size(1024) == "1.0KB"


def test_format_size_megabytes():
    assert cleanup.format_size(1024 * 1024) == "1.0MB"


def test_format_size_gigabytes():
    assert cleanup.format_size(1024 * 1024 * 1024) == "1.0GB"


def test_format_size_terabytes():
    assert cleanup.format_size(1024 * 1024 * 1024 * 1024) == "1.0TB"


# ============================================================================
# cleanup_cache: entries
# ============================================================================

def test_cleanup_cache_removes_old_entry(cachedir):
    entry = make_entry(cachedir, "old", age_days=91)

    stats = cleanup.cleanup_cache(cachedir, 90)

    assert not entry.exists()
    assert not (cachedir / "old.lock").exists()
    assert stats.entries == 1
    assert stats.size == 4
    assert stats.locks == 0
    assert stats.errors == 0


def test_cleanup_cache_keeps_recent_entry(cachedir):
    entry = make_entry(cachedir, "recent", age_days=89)

    stats = cleanup.cleanup_cache(cachedir, 90)

    assert entry.exists()
    assert (cachedir / "recent.lock").exists()
    assert stats.entries == 0


def test_cleanup_cache_dryrun(cachedir):
    entry = make_entry(cachedir, "old", age_days=91)

    stats = cleanup.cleanup_cache(cachedir, 90, dryrun=True)

    assert entry.exists()
    assert (cachedir / "old.lock").exists()
    assert stats.entries == 1
    assert stats.size == 4


def test_cleanup_cache_keeps_entry_without_lock(cachedir):
    '''An entry with no lock file has no access record, so it is never judged.'''
    entry = make_entry(cachedir, "nolock", lock=None)

    stats = cleanup.cleanup_cache(cachedir, 90)

    assert entry.exists()
    assert stats.entries == 0
    assert stats.locks == 0


def test_cleanup_cache_accepts_string_path(cachedir):
    entry = make_entry(cachedir, "old", age_days=91)

    assert cleanup.cleanup_cache(str(cachedir), 90).entries == 1
    assert not entry.exists()


def test_cleanup_cache_removes_readonly_entry(cachedir):
    '''Cache entries are read-only on disk; the sweep still has to remove them.'''
    entry = make_entry(cachedir, "old", age_days=91)
    (entry / "data.txt").chmod(0o444)
    entry.chmod(0o555)

    assert cleanup.cleanup_cache(cachedir, 90).entries == 1
    assert not entry.exists()


def unreadable(*names):
    '''Patch Path.stat to fail for these names only.

    Scoping it matters: pathlib implements exists() and is_file() on top of
    Path.stat on Python 3.12 and earlier, and an OSError carrying no errno is
    re-raised rather than read as "absent" -- so an unscoped patch fails
    somewhere different on every interpreter in the support matrix.
    '''
    real_stat = Path.stat

    def stat(self, *args, **kwargs):
        if self.name in names:
            raise OSError("boom")
        return real_stat(self, *args, **kwargs)

    return patch("pathlib.Path.stat", stat)


def test_cleanup_cache_reports_stat_error(cachedir, caplog):
    entry = make_entry(cachedir, "old", age_days=91)

    with unreadable("old.lock", "old.sc_lock"):
        stats = cleanup.cleanup_cache(cachedir, 90)

    assert entry.exists()
    assert stats.entries == 0
    assert stats.errors == 1
    assert "Could not stat lock file for old" in caplog.text


def test_cleanup_cache_reports_delete_error(cachedir, caplog):
    make_entry(cachedir, "old", age_days=91)

    with patch("shutil.rmtree", side_effect=OSError("boom")):
        stats = cleanup.cleanup_cache(cachedir, 90)

    assert stats.entries == 0
    assert stats.errors == 1
    assert "Failed to delete old" in caplog.text


def test_cleanup_cache_warns_when_lock_survives_entry(cachedir, caplog):
    '''The directory is gone either way; the lock becomes an orphan to retry.'''
    entry = make_entry(cachedir, "old", age_days=91)

    real_unlink = Path.unlink

    def fail_on_lock(self, *args, **kwargs):
        if self.suffix in cleanup.LOCK_SUFFIXES:
            raise OSError("held open")
        return real_unlink(self, *args, **kwargs)

    with patch("pathlib.Path.unlink", fail_on_lock):
        stats = cleanup.cleanup_cache(cachedir, 90)

    assert not entry.exists()
    assert (cachedir / "old.lock").exists()
    assert stats.entries == 1
    assert "Could not remove old.lock" in caplog.text


def test_cleanup_cache_logs_access_time(cachedir, caplog):
    make_entry(cachedir, "old", age_days=91)
    caplog.set_level(logging.INFO)

    cleanup.cleanup_cache(cachedir, 90)

    assert "Removing old (last accessed:" in caplog.text


# ============================================================================
# cleanup_cache: orphaned lock files (nothing else can ever collect these)
# ============================================================================

def test_cleanup_cache_removes_orphaned_lock(cachedir):
    lock_file = cachedir / "gone.lock"
    lock_file.touch()
    age_lock(lock_file, 91)

    stats = cleanup.cleanup_cache(cachedir, 90)

    assert not lock_file.exists()
    assert stats.locks == 1
    assert stats.entries == 0


def test_cleanup_cache_removes_orphaned_sc_lock(cachedir):
    lock_file = cachedir / "gone.sc_lock"
    lock_file.touch()
    age_lock(lock_file, 91)

    stats = cleanup.cleanup_cache(cachedir, 90)

    assert not lock_file.exists()
    assert stats.locks == 1


def test_cleanup_cache_removes_orphaned_lock_regardless_of_age(cachedir):
    '''A lock guarding a directory that does not exist is residue at any age.'''
    lock_file = cachedir / "gone.lock"
    lock_file.touch()
    age_lock(lock_file, 1)

    stats = cleanup.cleanup_cache(cachedir, 90)

    assert not lock_file.exists()
    assert stats.locks == 1


def test_cleanup_cache_spares_brand_new_orphaned_lock(cachedir):
    '''A lock this new may belong to a download that has yet to create its
    directory, which is the one case an orphan is not residue.'''
    lock_file = cachedir / "downloading.lock"
    lock_file.touch()

    stats = cleanup.cleanup_cache(cachedir, 90)

    assert lock_file.exists()
    assert stats.locks == 0


def test_cleanup_cache_collects_orphan_locks_just_past_the_window(cachedir):
    lock_file = cachedir / "gone.lock"
    lock_file.touch()
    when = datetime.now().timestamp() - cleanup.LOCK_ACTIVE_SECONDS - 60
    os.utime(lock_file, (when, when))

    assert cleanup.cleanup_cache(cachedir, 90).locks == 1
    assert not lock_file.exists()


def test_cleanup_cache_entries_only_pass(cachedir):
    '''collect_entries=False sweeps the locks and leaves every directory alone.'''
    entry = make_entry(cachedir, "old", age_days=91)
    orphan = cachedir / "gone.lock"
    orphan.touch()
    age_lock(orphan, 1)

    stats = cleanup.cleanup_cache(cachedir, 90, collect_entries=False)

    assert entry.exists()
    assert not orphan.exists()
    assert stats.entries == 0
    assert stats.locks == 1


def test_cleanup_cache_orphan_lock_vanishes_mid_sweep(cachedir):
    '''Another sweep, or a user, got there first.'''
    lock_file = cachedir / "gone.lock"
    lock_file.touch()
    age_lock(lock_file, 91)

    real_stat = Path.stat

    def vanish(self, *args, **kwargs):
        if self.name == "gone.lock":
            real_stat(self, *args, **kwargs)
            raise FileNotFoundError("gone")
        return real_stat(self, *args, **kwargs)

    with patch("pathlib.Path.stat", vanish):
        stats = cleanup.cleanup_cache(cachedir, 90)

    assert stats.locks == 0
    assert stats.errors == 0


def test_cleanup_cache_ignores_directory_named_like_a_lock(cachedir):
    trap = cachedir / "notreally.lock"
    trap.mkdir()

    stats = cleanup.cleanup_cache(cachedir, 90)

    assert trap.exists()
    assert stats.locks == 0
    assert stats.errors == 0


def test_cleanup_cache_keeps_lock_with_live_entry(cachedir):
    '''A lock guarding a directory that is still there is the first pass's business.'''
    make_entry(cachedir, "recent", age_days=89)

    stats = cleanup.cleanup_cache(cachedir, 90)

    assert (cachedir / "recent.lock").exists()
    assert stats.locks == 0


def test_cleanup_cache_orphan_lock_dryrun(cachedir):
    lock_file = cachedir / "gone.lock"
    lock_file.touch()
    age_lock(lock_file, 1)

    stats = cleanup.cleanup_cache(cachedir, 90, dryrun=True)

    assert lock_file.exists()
    assert stats.locks == 1


def test_cleanup_cache_removes_entry_lock_pair_once(cachedir):
    '''Removing an entry removes its lock, so the second pass must not double count.'''
    make_entry(cachedir, "old", age_days=91)

    stats = cleanup.cleanup_cache(cachedir, 90)

    assert stats.entries == 1
    assert stats.locks == 0
    assert not list(cachedir.iterdir())


def test_cleanup_cache_ignores_other_files(cachedir):
    '''Anything that is not a lock file or an entry is left alone.'''
    stamp = cachedir / cleanup.STAMP_FILE
    stamp.touch()
    age_lock(stamp, 400)

    other = cachedir / "notes.txt"
    other.write_text("keep me")
    age_lock(other, 400)

    stats = cleanup.cleanup_cache(cachedir, 90)

    assert stamp.exists()
    assert other.exists()
    assert stats.entries == 0
    assert stats.locks == 0


def test_cleanup_cache_orphan_lock_stat_error(cachedir, caplog):
    lock_file = cachedir / "gone.lock"
    lock_file.touch()
    age_lock(lock_file, 91)

    with unreadable("gone.lock"):
        stats = cleanup.cleanup_cache(cachedir, 90)

    assert lock_file.exists()
    assert stats.locks == 0
    assert stats.errors == 1
    assert "Could not stat lock file" in caplog.text


def test_cleanup_cache_orphan_lock_delete_error(cachedir, caplog):
    lock_file = cachedir / "gone.lock"
    lock_file.touch()
    age_lock(lock_file, 91)

    with patch("pathlib.Path.unlink", side_effect=OSError("boom")):
        stats = cleanup.cleanup_cache(cachedir, 90)

    assert stats.locks == 0
    assert stats.errors == 1
    assert "Failed to delete gone.lock" in caplog.text


# ============================================================================
# cleanup_cache: an entry another process is working on must survive
# ============================================================================

def test_cleanup_cache_skips_locked_entry(cachedir, caplog):
    entry = make_entry(cachedir, "old", age_days=91)
    caplog.set_level(logging.INFO)

    with patch("fasteners.InterProcessLock.acquire", return_value=False):
        stats = cleanup.cleanup_cache(cachedir, 90)

    assert entry.exists()
    assert stats.entries == 0
    assert "Skipping old, it is in use" in caplog.text


def test_cleanup_cache_skips_entry_with_live_fallback_lock(cachedir):
    '''A .sc_lock exists only while it is held, so a fresh one means a live download.'''
    entry = make_entry(cachedir, "old", age_days=91)
    (cachedir / "old.sc_lock").touch()

    stats = cleanup.cleanup_cache(cachedir, 90)

    assert entry.exists()
    assert stats.entries == 0


def test_cleanup_cache_removes_entry_with_stale_fallback_lock(cachedir):
    '''An old .sc_lock is residue from a killed process, not a live download.'''
    entry = make_entry(cachedir, "old", age_days=91)
    fallback = cachedir / "old.sc_lock"
    fallback.touch()
    age_lock(fallback, 91)

    stats = cleanup.cleanup_cache(cachedir, 90)

    assert not entry.exists()
    assert not fallback.exists()
    assert stats.entries == 1


def test_cleanup_cache_removes_entry_when_locking_unsupported(cachedir):
    '''Where flock does not work, resolve() falls back to the .sc_lock check.'''
    entry = make_entry(cachedir, "old", age_days=91)

    with patch("fasteners.InterProcessLock.acquire", side_effect=OSError("no flock")):
        stats = cleanup.cleanup_cache(cachedir, 90)

    assert not entry.exists()
    assert stats.entries == 1


def test_cleanup_cache_does_not_create_lock_to_delete_entry(cachedir):
    '''An entry guarded only by a .sc_lock must not leave a fresh .lock behind.'''
    entry = make_entry(cachedir, "old", age_days=91, lock=".sc_lock")

    stats = cleanup.cleanup_cache(cachedir, 90)

    assert not entry.exists()
    assert stats.entries == 1
    assert not list(cachedir.iterdir())


# ============================================================================
# auto_cleanup: the unattended sweep at the start of a local run
# ============================================================================

@pytest.fixture
def swept_cache(cachedir):
    '''A cache directory swept before, long enough ago to be swept again.'''
    stamp = cachedir / cleanup.STAMP_FILE
    stamp.touch()
    age_lock(stamp, cleanup.DEFAULT_INTERVAL + 1)
    return cachedir


def test_auto_cleanup_first_call_spares_entries(project, cachedir, caplog):
    '''An install upgrading into access tracking must not lose a cache it uses.

    Before the resolver stamped lock files, their mtime was the download time,
    so every entry looks as old as the day it was fetched. The orphaned locks
    have no such excuse and go on the first sweep.
    '''
    entry = make_entry(cachedir, "old", age_days=cleanup.DEFAULT_DAYS + 1)
    orphan = cachedir / "gone.lock"
    orphan.touch()
    age_lock(orphan, 1)
    caplog.set_level(logging.INFO)

    cleanup.auto_cleanup(project)

    assert entry.exists()
    assert not orphan.exists()
    assert (cachedir / cleanup.STAMP_FILE).exists()
    assert "Cleaned up 1 orphaned lock file" in caplog.text


def test_auto_cleanup_sweeps_after_baseline(project, swept_cache, caplog):
    entry = make_entry(swept_cache, "old", age_days=cleanup.DEFAULT_DAYS + 1)
    caplog.set_level(logging.INFO)

    cleanup.auto_cleanup(project)

    assert not entry.exists()
    assert "Cleaned up 1 cache entry (4.0B) not used in 90 days" in caplog.text


def test_auto_cleanup_default_is_forgiving(project, swept_cache):
    '''The unattended default spares anything used inside the default window.'''
    entry = make_entry(swept_cache, "old", age_days=cleanup.DEFAULT_DAYS - 1)

    cleanup.auto_cleanup(project)

    assert entry.exists()


def test_auto_cleanup_throttled_by_stamp(project, cachedir):
    stamp = cachedir / cleanup.STAMP_FILE
    stamp.touch()
    entry = make_entry(cachedir, "old", age_days=cleanup.DEFAULT_DAYS + 1)

    with patch.object(cleanup, "cleanup_cache") as sweep:
        cleanup.auto_cleanup(project)

    sweep.assert_not_called()
    assert entry.exists()


def test_auto_cleanup_refreshes_stamp(project, swept_cache):
    cleanup.auto_cleanup(project)

    age = datetime.now().timestamp() - (swept_cache / cleanup.STAMP_FILE).stat().st_mtime
    assert age < 60


def test_auto_cleanup_disabled_by_settings(project, swept_cache):
    MPManager.get_settings().set(cleanup.SETTINGS_CATEGORY, "cleanupdays", 0)
    entry = make_entry(swept_cache, "old", age_days=cleanup.DEFAULT_DAYS + 1)

    cleanup.auto_cleanup(project)

    assert entry.exists()
    # Disabled means untouched: no stamp refresh either
    assert datetime.now().timestamp() - \
        (swept_cache / cleanup.STAMP_FILE).stat().st_mtime > 60


def test_auto_cleanup_honors_settings_days(project, swept_cache):
    MPManager.get_settings().set(cleanup.SETTINGS_CATEGORY, "cleanupdays", 30)
    entry = make_entry(swept_cache, "old", age_days=31)
    assert 31 < cleanup.DEFAULT_DAYS, "must be a threshold the default would spare"

    cleanup.auto_cleanup(project)

    assert not entry.exists()


def test_auto_cleanup_honors_settings_interval(project, cachedir):
    MPManager.get_settings().set(cleanup.SETTINGS_CATEGORY, "cleanupinterval", 30)
    stamp = cachedir / cleanup.STAMP_FILE
    stamp.touch()
    age_lock(stamp, cleanup.DEFAULT_INTERVAL + 1)

    with patch.object(cleanup, "cleanup_cache") as sweep:
        cleanup.auto_cleanup(project)

    sweep.assert_not_called()


def test_auto_cleanup_bad_settings_fall_back_to_defaults(project, swept_cache, caplog):
    MPManager.get_settings().set(cleanup.SETTINGS_CATEGORY, "cleanupdays", "soon")
    entry = make_entry(swept_cache, "old", age_days=cleanup.DEFAULT_DAYS + 1)

    cleanup.auto_cleanup(project)

    assert not entry.exists()
    assert "Invalid cache cleanup settings" in caplog.text


def test_auto_cleanup_no_cache_dir(project):
    '''Nothing has been cached yet, so there is nothing to sweep or to stamp.'''
    with patch.object(cleanup, "cleanup_cache") as sweep:
        cleanup.auto_cleanup(project)

    sweep.assert_not_called()
    assert not Path("cache").exists()


def test_auto_cleanup_unstampable_cache_dir(project, cachedir, caplog):
    '''A sweep that cannot be throttled is worse than no sweep at all.'''
    project.logger.setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)

    with patch("pathlib.Path.touch", side_effect=OSError("read-only")), \
            patch.object(cleanup, "cleanup_cache") as sweep:
        cleanup.auto_cleanup(project)

    sweep.assert_not_called()
    assert "Could not record cache cleanup time" in caplog.text


def test_auto_cleanup_never_raises(project, swept_cache, caplog):
    '''Housekeeping must never be the reason a run does not start.'''
    project.logger.setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG)

    with patch.object(cleanup, "cleanup_cache", side_effect=RuntimeError("boom")):
        cleanup.auto_cleanup(project)

    assert "Cache cleanup skipped: boom (RuntimeError)" in caplog.text
