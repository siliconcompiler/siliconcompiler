# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
import sys
from pathlib import Path

from siliconcompiler import Project
from siliconcompiler.package import RemoteResolver
from siliconcompiler.package.cleanup import cleanup_cache, format_size, DEFAULT_DAYS


###########################
def main():
    progname = "cleanup"
    description = """
    ------------------------------------------------------------
    Utility script to clean up old cache entries.

    Scans the cache directory and removes entries that haven't been
    accessed in the specified number of days, using lock file modification
    times to determine access times. A .lock or .sc_lock file whose entry
    is already gone is removed whatever its age, unless it was taken in the
    last hour, which may mean another process is holding it.
    ------------------------------------------------------------
    """

    class CleanupProject(Project):
        def __init__(self):
            super().__init__()
            self._add_commandline_argument(
                "days", "int",
                "Remove cache entries older than this many days.",
                defvalue=DEFAULT_DAYS)
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

    try:
        stats = cleanup_cache(cachedir, days, dryrun=dryrun, logger=proj.logger)
    except Exception as e:
        proj.logger.error(f"Error scanning cache directory: {e}")
        return 1

    # Summary
    proj.logger.info(
        f"Cleanup complete: {stats.entries} entries removed "
        f"({format_size(stats.size)}), "
        f"{stats.locks} orphaned lock files removed"
    )

    if stats.errors > 0:
        proj.logger.warning(f"{stats.errors} errors occurred during cleanup")

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
