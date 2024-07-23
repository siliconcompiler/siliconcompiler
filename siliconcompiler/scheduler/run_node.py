#!/usr/bin/env python3

import argparse
import os
import sys
import tarfile
from siliconcompiler import Chip, Schema
from siliconcompiler.package import _path as sc_path
from siliconcompiler.scheduler import _runtask, _executenode
from siliconcompiler import __version__


##########################
def main():
    schema = Schema()

    # Can't use chip.cmdline because we don't want a bunch of extra logger information
    parser = argparse.ArgumentParser(prog='run_node',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description='Script to run a single node in an SC flowgraph')

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
                        required=True,
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
    args = parser.parse_args()

    # Change to working directory to allow rel path to be build dir
    # this avoids needing to deal with the job hash on the client
    # side
    os.chdir(args.cwd)

    # Create the Chip object.
    chip = Chip('<design>')
    chip.read_manifest(args.cfg)

    # setup work directory
    chip.set('arg', 'step', args.step)
    chip.set('arg', 'index', args.index)
    chip.set('option', 'builddir', args.builddir)
    chip.set('option', 'cachedir', args.cachedir)

    if args.remoteid:
        chip.set('record', 'remoteid', args.remoteid)

    if args.unset_scheduler:
        for vals, step, index in chip.schema._getvals('option', 'scheduler', 'name'):
            chip.unset('option', 'scheduler', 'name', step=step, index=index)

    # Init logger to ensure consistent view
    chip._init_logger(step=chip.get('arg', 'step'),
                      index=chip.get('arg', 'index'),
                      in_run=True)

    if args.cachemap:
        for cachepair in args.cachemap:
            package, path = cachepair.split(':')
            chip._packages[package] = path

    # Populate cache without downloading
    for package in chip.getkeys('package', 'source'):
        sc_path(chip, package, None)

    # Run the task.
    error = True
    try:
        _runtask(chip,
                 chip.get('option', 'flow'),
                 chip.get('arg', 'step'),
                 chip.get('arg', 'index'),
                 _executenode)
        error = False

    finally:
        if args.archive:
            # Archive the results.
            with tarfile.open(args.archive,
                              mode='w:gz') as tf:
                chip._archive_node(tf,
                                   step=args.step,
                                   index=args.index,
                                   include=args.include)

    # Return success/fail flag, in case the caller is interested.
    if error:
        return 1
    return 0


##########################
if __name__ == "__main__":
    sys.exit(main())
