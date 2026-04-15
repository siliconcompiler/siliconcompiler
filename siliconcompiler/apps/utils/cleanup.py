# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from siliconcompiler import Project
from siliconcompiler.package import RemoteResolver


###########################
def main():
    progname = "cleanup"
    description = """
    ------------------------------------------------------------
    Utility script to clean up old cache entries.

    Scans the cache directory and removes entries that haven't been
    accessed in the specified number of days. Uses lock file modification
    times to determine access times.
    ------------------------------------------------------------
    """

    class CleanupProject(Project):
        def __init__(self):
            super().__init__()
            self._add_commandline_argument(
                "days", "int",
                "Remove cache entries older than this many days.",
                defvalue=90)
            self._add_commandline_argument(
                "dryrun", "bool",
                "Show what would be deleted without actually deleting.",
                defvalue=False)
            self.option.unset("jobname")

    # Read command-line inputs and generate project objects to run the flow on.
    proj = CleanupProject.create_cmdline(
        progname,
        description=description,
        switchlist=[
            "-days",
            "-dryrun",
            "-cachedir"
        ],
        use_sources=False
    )

    # Get parameters
    days = proj.get("cmdarg", "days")
    dryrun = proj.get("cmdarg", "dryrun")

    # Determine cache directory
    cachedir_opt = proj.option.get_cachedir()
    if cachedir_opt:
        cachedir = Path(cachedir_opt).expanduser().resolve()
    else:
        cachedir = Path(RemoteResolver.determine_cache_dir(proj))

    if not cachedir.exists():
        proj.logger.error(f"Cache directory does not exist: {cachedir}")
        return 1

    if not cachedir.is_dir():
        proj.logger.error(f"Cache path is not a directory: {cachedir}")
        return 1

    proj.logger.info(f"Scanning cache directory: {cachedir}")
    proj.logger.info(f"Removing entries not accessed in {days} days")

    if dryrun:
        proj.logger.info("DRY RUN MODE - no files will be deleted")

    # Calculate cutoff time
    cutoff_time = datetime.now() - timedelta(days=days)
    cutoff_timestamp = cutoff_time.timestamp()

    deleted_count = 0
    deleted_size = 0
    error_count = 0

    # Scan cache directory for subdirectories with lock files
    try:
        for entry in cachedir.iterdir():
            if not entry.is_dir():
                continue

            # Look for associated lock file
            lock_file = cachedir / f"{entry.name}.lock"

            if not lock_file.exists():
                # Also try _make_readonly reference format with sc_lock
                sc_lock_file = cachedir / f"{entry.name}.sc_lock"
                if sc_lock_file.exists():
                    lock_file = sc_lock_file
                else:
                    # No lock file found, skip this directory
                    proj.logger.debug(f"No lock file found for {entry.name}, skipping")
                    continue

            # Get lock file modification time
            try:
                lock_mtime = lock_file.stat().st_mtime
            except OSError as e:
                proj.logger.warning(f"Could not stat lock file {lock_file}: {e}")
                error_count += 1
                continue

            # Check if entry is old enough to delete
            if lock_mtime < cutoff_timestamp:
                last_accessed = datetime.fromtimestamp(lock_mtime)

                # Calculate directory size
                try:
                    dir_size = sum(
                        f.stat().st_size for f in entry.rglob('*') if f.is_file()
                    )
                except OSError as e:
                    proj.logger.warning(f"Could not calculate size for {entry.name}: {e}")
                    dir_size = 0

                proj.logger.info(
                    f"Removing {entry.name} "
                    f"(last accessed: {last_accessed.isoformat()}, "
                    f"size: {_format_size(dir_size)})"
                )

                if not dryrun:
                    try:
                        # Make writable first (cache entries are read-only by default)
                        resolver = RemoteResolver("cleanup", proj, "", "")
                        resolver._make_writable(entry)

                        # Remove directory
                        shutil.rmtree(entry)

                        # Remove lock files
                        lock_file.unlink(missing_ok=True)
                        (cachedir / f"{entry.name}.sc_lock").unlink(missing_ok=True)

                        deleted_count += 1
                        deleted_size += dir_size
                    except Exception as e:
                        proj.logger.error(f"Failed to delete {entry.name}: {e}")
                        error_count += 1
                else:
                    deleted_count += 1
                    deleted_size += dir_size

    except Exception as e:
        proj.logger.error(f"Error scanning cache directory: {e}")
        return 1

    # Summary
    proj.logger.info(
        f"Cleanup complete: {deleted_count} entries removed "
        f"({_format_size(deleted_size)})"
    )

    if error_count > 0:
        proj.logger.warning(f"{error_count} errors occurred during cleanup")

    return 0


def _format_size(size_bytes):
    """Format bytes into human-readable size string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


#########################
if __name__ == "__main__":
    sys.exit(main())
