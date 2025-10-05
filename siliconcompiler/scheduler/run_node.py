#!/usr/bin/env python3
"""
A command-line utility to execute a single node (step and index) from a
SiliconCompiler flowgraph.

This script is designed to be called by a scheduler (like Slurm, Docker, or
a local process manager) to run a specific task in isolation. It takes all
necessary configuration information via command-line arguments, sets up a
project object, and executes the specified node's `run()` method.
"""

import argparse
import os
import sys
import tarfile
import os.path

from siliconcompiler import Project
from siliconcompiler.package import Resolver
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler import __version__


##########################
def main():
    """
    Run a single node (specified by step and index) from a SiliconCompiler project
    using command-line arguments.

    Parses CLI arguments to configure a Project (manifest, working directory, build/cache
    directories, step, index, remote id, and optional cache mappings), optionally
    unsets scheduler entries for local runs, executes the corresponding SchedulerNode,
    and optionally writes a gzipped tar archive of results.

    Returns:
        int: Exit code — 0 on successful node execution, 1 if the node failed.
    """
    # Can't use Project.cmdline because we don't want a bunch of extra logger information
    parser = argparse.ArgumentParser(prog='run_node',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description='Script to run a single node in an SC flowgraph')

    # Define command-line arguments
    parser.add_argument('-version',
                        action='version',
                        version=__version__)
    parser.add_argument('-cfg',
                        required=True,
                        metavar='<file>',
                        help="Option: configuration manifest")
    parser.add_argument('-cwd',
                        required=True,
                        metavar='<directory>',
                        help='Run current working directory')
    parser.add_argument('-builddir',
                        metavar='<directory>',
                        required=True,
                        help="Option: build directory")
    parser.add_argument('-cachedir',
                        metavar='<directory>',
                        help="Option: user cache directory")
    parser.add_argument('-cachemap',
                        metavar='<package>:<directory>',
                        nargs='+',
                        help='Map of caches to prepopulate runner with')
    parser.add_argument('-step',
                        required=True,
                        metavar='<step>',
                        help="ARG: step argument")
    parser.add_argument('-index',
                        required=True,
                        metavar='<index>',
                        help="ARG: index argument")
    parser.add_argument('-remoteid',
                        metavar='<id>',
                        help="Record: remote job ID")
    parser.add_argument('-archive',
                        metavar='<file>',
                        help='Generate archive')
    parser.add_argument('-include',
                        metavar='<path>',
                        nargs='+',
                        help='Files to include in archive')
    parser.add_argument('-unset_scheduler',
                        action='store_true',
                        help='Unset scheduler to ensure local run')
    parser.add_argument('-replay',
                        action='store_true',
                        help='Running as replay')
    args = parser.parse_args()

    # Change to the specified working directory. This is crucial for remote
    # runners (like Docker) where paths inside the environment are different
    # from the host.
    os.chdir(os.path.abspath(args.cwd))

    # Create the project object.
    proj = Project.from_manifest(filepath=args.cfg)

    # Configure the project object based on command-line arguments.
    proj.set('arg', 'step', args.step)
    proj.set('arg', 'index', args.index)
    proj.set('option', 'builddir', os.path.abspath(args.builddir))

    if args.cachedir:
        proj.set('option', 'cachedir', os.path.abspath(args.cachedir))

    if args.remoteid:
        proj.set('record', 'remoteid', args.remoteid)

    # If running in a container/remote machine, we unset the scheduler to
    # prevent a recursive scheduling loop.
    if args.unset_scheduler:
        for _, step, index in proj.get('option', 'scheduler', 'name',
                                       field=None).getvalues():
            proj.unset('option', 'scheduler', 'name', step=step, index=index)

    # Pre-populate the package cache if a map is provided.
    if args.cachemap:
        for cachepair in args.cachemap:
            package, path = cachepair.split(':')
            Resolver.set_cache(proj, package, path)

    # Instantiate the SchedulerNode for the specified step and index.
    error = True
    node = SchedulerNode(
        proj,
        args.step,
        args.index,
        replay=args.replay)
    try:
        # Execute the node's run() method.
        node.run()
        error = False
    finally:
        # Archive results upon completion, regardless of success or failure.
        if args.archive:
            with tarfile.open(args.archive,
                              mode='w:gz') as tf:
                node.archive(tf, include=args.include)

    # Return a non-zero exit code on error.
    if error:
        return 1
    return 0


##########################
if __name__ == "__main__":
    # This makes the script executable.
    sys.exit(main())
