#!/usr/bin/env python3
"""
A command-line utility to execute a single node (step and index) from a
SiliconCompiler flowgraph.

This script is designed to be called by a scheduler (like Slurm, Docker, or
a local process manager) to run a specific task in isolation. It takes all
necessary configuration information via command-line arguments, sets up a
Chip object, and executes the specified node's `run()` method.
"""

import argparse
import os
import sys
import tarfile
import os.path

from siliconcompiler import Chip, Schema
from siliconcompiler.package import Resolver
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler import __version__


##########################
def main():
    """The main entry point for the run_node script."""
    schema = Schema()

    # Set up a minimal argument parser, as we don't need the full
    # Chip.cmdline() functionality which includes extra logger setup.
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
                        help=schema.get('option', 'cfg',
                                        field='shorthelp'))
    parser.add_argument('-cwd',
                        required=True,
                        metavar='<directory>',
                        help='Run current working directory')
    parser.add_argument('-builddir',
                        metavar='<directory>',
                        required=True,
                        help=schema.get('option', 'builddir',
                                        field='shorthelp'))
    parser.add_argument('-cachedir',
                        metavar='<directory>',
                        help=schema.get('option', 'cachedir',
                                        field='shorthelp'))
    parser.add_argument('-cachemap',
                        metavar='<package>:<directory>',
                        nargs='+',
                        help='Map of caches to prepopulate runner with')
    parser.add_argument('-step',
                        required=True,
                        metavar='<step>',
                        help=schema.get('arg', 'step',
                                        field='shorthelp'))
    parser.add_argument('-index',
                        required=True,
                        metavar='<index>',
                        help=schema.get('arg', 'index',
                                        field='shorthelp'))
    parser.add_argument('-remoteid',
                        metavar='<id>',
                        help=schema.get('record', 'remoteid',
                                        field='shorthelp'))
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

    # Create the Chip object.
    chip = Chip('<design>')
    # Load the configuration from the manifest provided.
    chip.read_manifest(args.cfg)

    # Configure the chip object based on command-line arguments.
    chip.set('arg', 'step', args.step)
    chip.set('arg', 'index', args.index)
    chip.set('option', 'builddir', os.path.abspath(args.builddir))

    if args.cachedir:
        chip.set('option', 'cachedir', os.path.abspath(args.cachedir))

    if args.remoteid:
        chip.set('record', 'remoteid', args.remoteid)

    # If running in a container/remote machine, we unset the scheduler to
    # prevent a recursive scheduling loop.
    if args.unset_scheduler:
        for _, step, index in chip.get('option', 'scheduler', 'name',
                                       field=None).getvalues():
            chip.unset('option', 'scheduler', 'name', step=step, index=index)

    # Pre-populate the package cache if a map is provided.
    if args.cachemap:
        for cachepair in args.cachemap:
            package, path = cachepair.split(':')
            Resolver.set_cache(chip, package, path)

    # Ensure all package caches are populated before running the node.
    for resolver in chip.get('package', field='schema').get_resolvers().values():
        resolver()

    # Instantiate the SchedulerNode for the specified step and index.
    error = True
    node = SchedulerNode(
        chip,
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
