# Copyright 2024 Silicon Compiler Authors. All Rights Reserved.
import pytest
import os

from datetime import datetime, timedelta

from siliconcompiler.apps.utils import cleanup


@pytest.fixture
def temp_cache_dir(tmp_path):
    '''Create a temporary cache directory for testing.'''
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def cache_with_old_entries(temp_cache_dir):
    '''Create a cache directory with both old and new entries.'''
    # Create an old entry (91 days ago)
    old_entry = temp_cache_dir / "old-entry-1234567890ab"
    old_entry.mkdir()
    (old_entry / "data.txt").write_text("old data")
    (old_entry / "subdir").mkdir()
    (old_entry / "subdir" / "file.txt").write_text("more old data")

    old_lock = temp_cache_dir / "old-entry-1234567890ab.lock"
    old_lock.touch()
    old_time = (datetime.now() - timedelta(days=91)).timestamp()
    os.utime(old_lock, (old_time, old_time))

    # Create a recent entry (30 days ago)
    recent_entry = temp_cache_dir / "recent-entry-abcdef123456"
    recent_entry.mkdir()
    (recent_entry / "data.txt").write_text("recent data")

    recent_lock = temp_cache_dir / "recent-entry-abcdef123456.lock"
    recent_lock.touch()
    recent_time = (datetime.now() - timedelta(days=30)).timestamp()
    os.utime(recent_lock, (recent_time, recent_time))

    # Create a very recent entry (5 days ago)
    very_recent_entry = temp_cache_dir / "very-recent-entry-xyz789def012"
    very_recent_entry.mkdir()
    (very_recent_entry / "data.txt").write_text("very recent data")

    very_recent_lock = temp_cache_dir / "very-recent-entry-xyz789def012.lock"
    very_recent_lock.touch()

    return temp_cache_dir


# ============================================================================
# Tests for basic functionality
# ============================================================================

def test_cleanup_dry_run(monkeypatch, cache_with_old_entries, capsys):
    '''Test cleanup in dry-run mode does not delete anything.'''
    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-dryrun',
        '-cachedir', str(cache_with_old_entries)
    ])

    result = cleanup.main()
    assert result == 0

    # Verify old entry still exists
    old_entry = cache_with_old_entries / "old-entry-1234567890ab"
    assert old_entry.exists()
    assert (old_entry / "data.txt").exists()

    # Check output shows what would be deleted
    output = capsys.readouterr().out
    assert "DRY RUN MODE" in output
    assert "old-entry-1234567890ab" in output


def test_cleanup_actual_deletion(monkeypatch, cache_with_old_entries):
    '''Test cleanup actually deletes old entries when not in dry-run mode.'''
    old_entry = cache_with_old_entries / "old-entry-1234567890ab"
    recent_entry = cache_with_old_entries / "recent-entry-abcdef123456"

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-cachedir', str(cache_with_old_entries)
    ])

    result = cleanup.main()
    assert result == 0

    # Verify old entry is deleted
    assert not old_entry.exists()
    assert not (cache_with_old_entries / "old-entry-1234567890ab.lock").exists()

    # Verify recent entry still exists
    assert recent_entry.exists()


def test_cleanup_preserves_recent_entries(monkeypatch, cache_with_old_entries):
    '''Test cleanup preserves entries newer than the threshold.'''
    very_recent_entry = cache_with_old_entries / "very-recent-entry-xyz789def012"
    recent_entry = cache_with_old_entries / "recent-entry-abcdef123456"

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-cachedir', str(cache_with_old_entries)
    ])

    cleanup.main()

    # Verify recent entries still exist
    assert recent_entry.exists()
    assert very_recent_entry.exists()


def test_cleanup_different_threshold(monkeypatch, cache_with_old_entries):
    '''Test cleanup with different day threshold.'''
    old_entry = cache_with_old_entries / "old-entry-1234567890ab"
    recent_entry = cache_with_old_entries / "recent-entry-abcdef123456"

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '20',  # Only delete entries older than 20 days
        '-cachedir', str(cache_with_old_entries)
    ])

    cleanup.main()

    # Old entry should be deleted
    assert not old_entry.exists()

    # Recent entry (30 days) should also be deleted
    assert not recent_entry.exists()


# ============================================================================
# Tests for edge cases
# ============================================================================

def test_cleanup_nonexistent_cache_dir(monkeypatch, tmp_path):
    '''Test cleanup handles nonexistent cache directory gracefully.'''
    nonexistent = tmp_path / "nonexistent_cache"

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-cachedir', str(nonexistent)
    ])

    result = cleanup.main()
    assert result == 1


def test_cleanup_empty_cache_dir(monkeypatch, temp_cache_dir):
    '''Test cleanup handles empty cache directory.'''
    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-cachedir', str(temp_cache_dir)
    ])

    result = cleanup.main()
    assert result == 0


def test_cleanup_entry_without_lock_file(monkeypatch, temp_cache_dir):
    '''Test cleanup skips entries without lock files.'''
    orphan_entry = temp_cache_dir / "orphan-entry-no-lock"
    orphan_entry.mkdir()
    (orphan_entry / "data.txt").write_text("orphan data")

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '0',  # Delete everything
        '-cachedir', str(temp_cache_dir)
    ])

    cleanup.main()

    # Orphan entry should still exist (no lock file to check)
    assert orphan_entry.exists()


def test_cleanup_with_sc_lock_file(monkeypatch, temp_cache_dir):
    '''Test cleanup handles sc_lock files as fallback.'''
    entry = temp_cache_dir / "entry-with-sc-lock"
    entry.mkdir()
    (entry / "data.txt").write_text("data")

    # Create sc_lock file instead of regular lock
    sc_lock = temp_cache_dir / "entry-with-sc-lock.sc_lock"
    sc_lock.touch()
    old_time = (datetime.now() - timedelta(days=91)).timestamp()
    os.utime(sc_lock, (old_time, old_time))

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-cachedir', str(temp_cache_dir)
    ])

    cleanup.main()

    # Entry should be deleted using sc_lock as reference
    assert not entry.exists()


# ============================================================================
# Tests for error handling
# ============================================================================

def test_cleanup_stat_error_handling(monkeypatch, temp_cache_dir, capsys):
    '''Test cleanup handles entries with unreadable lock files gracefully.'''
    entry = temp_cache_dir / "entry-readable"
    entry.mkdir()
    (entry / "data.txt").write_text("data")

    lock_file = temp_cache_dir / "entry-readable.lock"
    lock_file.touch()
    old_time = (datetime.now() - timedelta(days=91)).timestamp()
    os.utime(lock_file, (old_time, old_time))

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-cachedir', str(temp_cache_dir)
    ])

    result = cleanup.main()
    assert result == 0
    assert not entry.exists()


def test_cleanup_cache_dir_is_file(monkeypatch, tmp_path):
    '''Test cleanup handles cache path being a file, not directory.'''
    cache_file = tmp_path / "cache_file"
    cache_file.write_text("not a directory")

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-cachedir', str(cache_file)
    ])

    result = cleanup.main()
    assert result == 1


# ============================================================================
# Tests for lock file handling
# ============================================================================

def test_cleanup_removes_both_lock_types(monkeypatch, temp_cache_dir):
    '''Test cleanup removes both .lock and .sc_lock files.'''
    entry = temp_cache_dir / "entry-with-locks"
    entry.mkdir()
    (entry / "data.txt").write_text("data")

    lock_file = temp_cache_dir / "entry-with-locks.lock"
    sc_lock_file = temp_cache_dir / "entry-with-locks.sc_lock"
    lock_file.touch()
    sc_lock_file.touch()

    old_time = (datetime.now() - timedelta(days=91)).timestamp()
    os.utime(lock_file, (old_time, old_time))

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-cachedir', str(temp_cache_dir)
    ])

    cleanup.main()

    assert not entry.exists()
    assert not lock_file.exists()
    assert not sc_lock_file.exists()


def test_cleanup_lock_file_time_is_used(monkeypatch, temp_cache_dir):
    '''Test that lock file modification time is used for age determination.'''
    entry = temp_cache_dir / "entry-old-data-new-lock"
    entry.mkdir()
    (entry / "data.txt").write_text("data")

    lock_file = temp_cache_dir / "entry-old-data-new-lock.lock"
    lock_file.touch()
    # Lock file is very recent
    recent_time = (datetime.now() - timedelta(days=1)).timestamp()
    os.utime(lock_file, (recent_time, recent_time))

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-cachedir', str(temp_cache_dir)
    ])

    cleanup.main()

    # Entry should NOT be deleted because lock file is recent
    assert entry.exists()


# ============================================================================
# Tests for size calculations
# ============================================================================

def test_cleanup_calculates_size(monkeypatch, cache_with_old_entries, capsys):
    '''Test cleanup correctly calculates directory sizes.'''
    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-dryrun',
        '-cachedir', str(cache_with_old_entries)
    ])

    cleanup.main()

    output = capsys.readouterr().out
    # Should show size in output
    assert "size:" in output
    assert "-entry-1234567890ab" in output


def test_format_size_bytes():
    '''Test _format_size with bytes.'''
    assert cleanup._format_size(512) == "512.0B"


def test_format_size_kilobytes():
    '''Test _format_size with kilobytes.'''
    assert cleanup._format_size(1024) == "1.0KB"


def test_format_size_megabytes():
    '''Test _format_size with megabytes.'''
    assert cleanup._format_size(1024 * 1024) == "1.0MB"


def test_format_size_gigabytes():
    '''Test _format_size with gigabytes.'''
    assert cleanup._format_size(1024 * 1024 * 1024) == "1.0GB"


def test_format_size_terabytes():
    '''Test _format_size with terabytes.'''
    assert cleanup._format_size(1024 * 1024 * 1024 * 1024) == "1.0TB"


def test_cleanup_summary_shows_total_size(monkeypatch, cache_with_old_entries, capsys):
    '''Test cleanup summary shows total size removed.'''
    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-dryrun',
        '-cachedir', str(cache_with_old_entries)
    ])

    cleanup.main()

    output = capsys.readouterr().out
    assert "Cleanup complete:" in output
    assert "entries removed" in output


# ============================================================================
# Tests for command-line arguments
# ============================================================================

def test_cleanup_default_days(monkeypatch, cache_with_old_entries):
    '''Test cleanup uses default 90 days when not specified.'''
    # Entry is 91 days old
    old_entry = cache_with_old_entries / "old-entry-1234567890ab"

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-cachedir', str(cache_with_old_entries)
    ])

    cleanup.main()

    # Should be deleted with default 90 days
    assert not old_entry.exists()


def test_cleanup_default_dryrun_false(monkeypatch, cache_with_old_entries):
    '''Test cleanup performs actual deletion by default (not dryrun).'''
    old_entry = cache_with_old_entries / "old-entry-1234567890ab"

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-cachedir', str(cache_with_old_entries)
    ])

    cleanup.main()

    # Should actually delete
    assert not old_entry.exists()


def test_cleanup_dryrun_true_prevents_deletion(monkeypatch, cache_with_old_entries):
    '''Test cleanup with -dryrun true does not delete.'''
    old_entry = cache_with_old_entries / "old-entry-1234567890ab"

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-dryrun', 'true',
        '-cachedir', str(cache_with_old_entries)
    ])

    cleanup.main()

    assert old_entry.exists()


# ============================================================================
# Tests for read-only cache handling
# ============================================================================

def test_cleanup_handles_readonly_entries(monkeypatch, cache_with_old_entries):
    '''Test cleanup can delete read-only cache entries.'''
    old_entry = cache_with_old_entries / "old-entry-1234567890ab"

    # Make entry and contents read-only
    for item in old_entry.rglob('*'):
        if item.is_file():
            os.chmod(item, 0o444)
    os.chmod(old_entry, 0o555)

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-cachedir', str(cache_with_old_entries)
    ])

    result = cleanup.main()
    assert result == 0

    # Should be able to delete read-only files
    assert not old_entry.exists()


# ============================================================================
# Tests for logging and output
# ============================================================================

def test_cleanup_logs_cache_directory(monkeypatch, temp_cache_dir, capsys):
    '''Test cleanup logs the cache directory being scanned.'''
    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-cachedir', str(temp_cache_dir)
    ])

    cleanup.main()

    output = capsys.readouterr().out
    assert "Scanning cache directory:" in output
    assert str(temp_cache_dir) in output


def test_cleanup_logs_deletion_plan(monkeypatch, cache_with_old_entries, capsys):
    '''Test cleanup logs what entries it will remove.'''
    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-dryrun',
        '-cachedir', str(cache_with_old_entries)
    ])

    cleanup.main()

    output = capsys.readouterr().out
    assert "Removing" in output
    assert "last accessed:" in output


def test_cleanup_logs_days_threshold(monkeypatch, temp_cache_dir, capsys):
    '''Test cleanup logs the age threshold.'''
    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '42',
        '-cachedir', str(temp_cache_dir)
    ])

    cleanup.main()

    output = capsys.readouterr().out
    assert "Removing entries not accessed in 42 days" in output


# ============================================================================
# Tests for complex scenarios
# ============================================================================

def test_cleanup_mixed_old_recent_and_no_lock(monkeypatch, temp_cache_dir):
    '''Test cleanup with mix of old, recent, and entries without lock files.'''
    # Old entry
    old_entry = temp_cache_dir / "old-entry"
    old_entry.mkdir()
    (old_entry / "data.txt").write_text("old")
    old_lock = temp_cache_dir / "old-entry.lock"
    old_lock.touch()
    old_time = (datetime.now() - timedelta(days=100)).timestamp()
    os.utime(old_lock, (old_time, old_time))

    # Recent entry
    recent_entry = temp_cache_dir / "recent-entry"
    recent_entry.mkdir()
    (recent_entry / "data.txt").write_text("recent")
    recent_lock = temp_cache_dir / "recent-entry.lock"
    recent_lock.touch()

    # No lock entry
    no_lock_entry = temp_cache_dir / "no-lock-entry"
    no_lock_entry.mkdir()
    (no_lock_entry / "data.txt").write_text("no lock")

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-cachedir', str(temp_cache_dir)
    ])

    cleanup.main()

    # Old should be deleted
    assert not old_entry.exists()

    # Recent should remain
    assert recent_entry.exists()

    # No lock should remain (skipped)
    assert no_lock_entry.exists()


def test_cleanup_multiple_old_entries(monkeypatch, temp_cache_dir):
    '''Test cleanup with multiple old entries at different ages.'''
    # Create multiple old entries at different times
    for i in range(3):
        entry = temp_cache_dir / f"old-entry-{i}"
        entry.mkdir()
        (entry / "data.txt").write_text(f"data {i}")

        lock = temp_cache_dir / f"old-entry-{i}.lock"
        lock.touch()
        old_time = (datetime.now() - timedelta(days=100 + i * 10)).timestamp()
        os.utime(lock, (old_time, old_time))

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-cachedir', str(temp_cache_dir)
    ])

    result = cleanup.main()
    assert result == 0

    # All old entries should be deleted
    for i in range(3):
        assert not (temp_cache_dir / f"old-entry-{i}").exists()


def test_cleanup_with_nested_directories(monkeypatch, temp_cache_dir):
    '''Test cleanup correctly handles size calculation with nested directories.'''
    entry = temp_cache_dir / "nested-entry"
    entry.mkdir()

    # Create nested structure
    for level1 in range(2):
        l1_dir = entry / f"level1_{level1}"
        l1_dir.mkdir()
        for level2 in range(2):
            l2_dir = l1_dir / f"level2_{level2}"
            l2_dir.mkdir()
            for level3 in range(2):
                (l2_dir / f"file_{level3}.txt").write_text("x" * 1000)

    lock = temp_cache_dir / "nested-entry.lock"
    lock.touch()
    old_time = (datetime.now() - timedelta(days=91)).timestamp()
    os.utime(lock, (old_time, old_time))

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-days', '90',
        '-cachedir', str(temp_cache_dir)
    ])

    cleanup.main()

    assert not entry.exists()
    assert not lock.exists()


# ============================================================================
# Tests for return codes
# ============================================================================

def test_cleanup_returns_zero_on_success(monkeypatch, temp_cache_dir):
    '''Test cleanup returns 0 on success.'''
    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-cachedir', str(temp_cache_dir)
    ])

    result = cleanup.main()
    assert result == 0


def test_cleanup_returns_one_on_nonexistent_cachedir(monkeypatch, tmp_path):
    '''Test cleanup returns 1 when cache directory does not exist.'''
    nonexistent = tmp_path / "nonexistent"

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-cachedir', str(nonexistent)
    ])

    result = cleanup.main()
    assert result == 1


def test_cleanup_returns_one_when_cachedir_is_file(monkeypatch, tmp_path):
    '''Test cleanup returns 1 when cache path is a file.'''
    cache_file = tmp_path / "cache"
    cache_file.write_text("not a dir")

    monkeypatch.setattr('sys.argv', [
        'cleanup',
        '-cachedir', str(cache_file)
    ])

    result = cleanup.main()
    assert result == 1
