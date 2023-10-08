# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import copy
import json
import os
import sys

from siliconcompiler import Chip
from siliconcompiler import SiliconCompilerError
from siliconcompiler._metadata import default_server
from siliconcompiler.remote.client import (cancel_job, check_progress, delete_job,
                                           remote_ping, remote_run_loop, configure)
from siliconcompiler.utils import default_credentials_file


def main():
    progname = "sc-remote"
    description = """
-----------------------------------------------------------
SC app that provides an entry point to common remote / server
interactions.

To generate a configuration file, use:
    sc-remote -configure

    or to specify a specific server and/or port:
    sc-remote -configure -server https://example.com
    sc-remote -configure -server https://example.com:1234

To check an ongoing job's progress, use:
    sc-remote -cfg <stepdir>/outputs/<design>.pkg.json

To cancel an ongoing job, use:
    sc-remote -cancel -cfg <stepdir>/outputs/<design>.pkg.json

To reconnect an ongoing job, use:
    sc-remote -reconnect -cfg <stepdir>/outputs/<design>.pkg.json

To delete a job, use:
    sc-remote -delete -cfg <stepdir>/outputs/<design>.pkg.json
-----------------------------------------------------------
"""

    # Argument Parser
    progname = 'sc-remote'
    chip = Chip(progname)
    switchlist = ['-cfg', '-credentials']
    extra_args = {
        '-configure': {'action': 'store_true',
                       'help': 'create configuration file for the remote'},
        '-server': {'help': 'address of server for configure',
                    'metavar': '<server>'},
        '-reconnect': {'action': 'store_true',
                       'help': 'reconnect to a running job on the remote'},
        '-cancel': {'action': 'store_true',
                    'help': 'cancel a running job on the remote'},
        '-delete': {'action': 'store_true',
                    'help': 'delete a job on the remote'},
    }

    try:
        args = chip.create_cmdline(progname,
                                   switchlist=switchlist,
                                   additional_args=extra_args,
                                   description=description)
    except Exception as e:
        chip.logger.error(e)
        return 1

    # Sanity checks.
    exclusive = ['configure', 'reconnect', 'cancel', 'delete']
    cfg_only = ['reconnect', 'cancel', 'delete']

    exclusive_count = sum([1 for arg in exclusive if args[arg]])
    if exclusive_count > 1:
        chip.logger.error(f'Error: {", ".join(["-"+e for e in exclusive])} are mutually exclusive')
        return 1
    chip_cfg = chip.get('option', 'cfg')
    if chip_cfg and not any([args[arg] for arg in cfg_only]):
        chip.logger.error(f'Error: -cfg is required for {", ".join(["-"+e for e in cfg_only])}')
    if any([args[arg] for arg in cfg_only]) and args['server']:
        chip.logger.error('Error: -server cannot be specified with '
                          f'{", ".join(["-"+e for e in cfg_only])}')

    if args['configure']:
        try:
            configure(chip, server=args['server'])
        except ValueError as e:
            chip.logger.error(e)
            return 1
        return 0

    # Read in credentials from file, if specified and available.
    # Otherwise, use the default server address.
    if not chip.get('option', 'credentials'):
        chip.set('option', 'credentials', default_credentials_file())

    if os.path.isfile(chip.get('option', 'credentials')):
        with open(chip.get('option', 'credentials'), 'r') as cfgf:
            try:
                remote_cfg = json.loads(cfgf.read())
            except json.JSONDecodeError:
                chip.logger.error('Error reading remote configuration file: invalid JSON')
                return 1
    else:
        # TODO: I think this default is stored somewhere - client.py? _metadata.py?
        remote_cfg = {'address': default_server}

    # Main logic.
    # If no job-related options are specified, fetch and report basic info.
    # Create temporary Chip object and check on the server.
    chip.status['remote_cfg'] = remote_cfg
    try:
        remote_ping(chip)
    except SiliconCompilerError as e:
        chip.logger.error(f'{e}')
        return 1

    # If the -cancel flag is specified, cancel the job.
    if args['cancel']:
        try:
            cancel_job(chip)
        except SiliconCompilerError as e:
            chip.logger.error(f'{e}')
            return 1

    # If the -delete flag is specified, delete the job.
    elif args['delete']:
        try:
            delete_job(chip)
        except SiliconCompilerError as e:
            chip.logger.error(f'{e}')
            return 1

    # If the -reconnect flag is specified, re-enter the client flow
    # in its "check_progress/ until job is done" loop.
    elif args['reconnect']:
        # Start from succesors of entry nodes, so entry nodes are not fetched from remote.
        environment = copy.deepcopy(os.environ)
        entry_nodes = chip._get_flowgraph_entry_nodes(chip.get('option', 'flow'))
        flow = chip.get('option', 'flow')
        entry_nodes = chip._get_flowgraph_entry_nodes(flow)
        for entry_node in entry_nodes:
            outputs = chip._get_flowgraph_node_outputs(flow, entry_node)
            chip.set('option', 'from', list(map(lambda node: node[0], outputs)))
        # Enter the remote run loop.
        chip._init_logger(step='remote', index='0', in_run=True)
        try:
            remote_run_loop(chip)
        except SiliconCompilerError as e:
            chip.logger.error(f'{e}')
            return 1
        # Summarize the run.
        chip._finalize_run(chip.nodes_to_execute(), environment)
        chip.summary()

    # If only a manifest is specified, make a 'check_progress/' request and report results:
    elif chip_cfg:
        try:
            check_progress(chip)
        except SiliconCompilerError as e:
            chip.logger.error(f'{e}')
            return 1

    # Done
    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
