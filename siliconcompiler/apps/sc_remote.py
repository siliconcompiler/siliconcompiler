# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import os
import sys

from siliconcompiler import Chip
from siliconcompiler import SiliconCompilerError
from siliconcompiler.remote.client import Client, ConfigureClient
from siliconcompiler.scheduler import _finalize_run
from siliconcompiler.flowgraph import RuntimeFlowgraph


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

    to add or remove directories from upload whitelist, these
        also support globbing:
    sc-remote -configure -add ./fine_to_upload
    sc-remote -configure -remove ./no_longer_okay_to_upload

    to display the full configuration of the credentials file
    sc-remote -configure -list

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
                       'help': 'create configuration file for the remote',
                       'sc_print': False},
        '-server': {'help': 'address of server for configure (only valid with -configure)',
                    'metavar': '<server>',
                    'sc_print': False},
        '-add': {'help': 'path to add to the upload whitelist (only valid with -configure)',
                 'metavar': '<path>',
                 'nargs': '+',
                 'sc_print': False},
        '-remove': {'help': 'path to remove from the upload whitelist (only valid with -configure)',
                    'metavar': '<path>',
                    'nargs': '+',
                    'sc_print': False},
        '-list': {'help': 'print the current configuration (only valid with -configure)',
                  'action': 'store_true',
                  'sc_print': False},
        '-reconnect': {'action': 'store_true',
                       'help': 'reconnect to a running job on the remote',
                       'sc_print': False},
        '-cancel': {'action': 'store_true',
                    'help': 'cancel a running job on the remote',
                    'sc_print': False},
        '-delete': {'action': 'store_true',
                    'help': 'delete a job on the remote',
                    'sc_print': False},
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
    if not chip_cfg and any([args[arg] for arg in cfg_only]):
        chip.logger.error(f'Error: -cfg is required for {", ".join(["-"+e for e in cfg_only])}')
        return 2
    if any([args[arg] for arg in cfg_only]) and args['server']:
        chip.logger.error('Error: -server cannot be specified with '
                          f'{", ".join(["-"+e for e in cfg_only])}')

    if args['configure']:
        if args['list']:
            client = Client(chip)
            client.print_configuration()
            return 0

        if not args['add'] and not args['remove']:
            try:
                client = ConfigureClient(chip)
                client.configure_server(server=args['server'])
            except ValueError as e:
                chip.logger.error(e)
                return 1
        else:
            try:
                client = ConfigureClient(chip)
                client.configure_whitelist(add=args['add'], remove=args['remove'])
            except ValueError as e:
                chip.logger.error(e)
                return 1

        return 0

    client = Client(chip)
    # Main logic.
    # If no job-related options are specified, fetch and report basic info.
    # Create temporary Chip object and check on the server.
    try:
        client.check()
    except SiliconCompilerError as e:
        chip.logger.error(f'{e}')
        return 1

    # If the -cancel flag is specified, cancel the job.
    if args['cancel']:
        try:
            client.cancel_job()
        except SiliconCompilerError as e:
            chip.logger.error(f'{e}')
            return 1

    # If the -delete flag is specified, delete the job.
    elif args['delete']:
        try:
            client.delete_job()
        except SiliconCompilerError as e:
            chip.logger.error(f'{e}')
            return 1

    # If the -reconnect flag is specified, re-enter the client flow
    # in its "check_progress/ until job is done" loop.
    elif args['reconnect']:
        # Start from successors of entry nodes, so entry nodes are not fetched from remote.
        flow = chip.get('option', 'flow')
        entry_nodes = chip.schema.get("flowgraph", flow, field="schema").get_entry_nodes()
        for entry_node in entry_nodes:
            outputs = chip.schema.get("flowgraph", flow,
                                      field='schema').get_node_outputs(*entry_node)
            chip.set('option', 'from', list(map(lambda node: node[0], outputs)))
        # Enter the remote run loop.
        try:
            client._run_loop()
        except SiliconCompilerError as e:
            chip.logger.error(f'{e}')
            return 1

        # Wrap up run
        runtime = RuntimeFlowgraph(
            chip.schema.get("flowgraph", flow, field='schema'),
            from_steps=chip.get('option', 'from'),
            to_steps=chip.get('option', 'to'),
            prune_nodes=chip.get('option', 'prune'))
        for step, index in runtime.get_nodes():
            manifest = os.path.join(chip.getworkdir(step=step, index=index),
                                    'outputs',
                                    f'{chip.design}.pkg.json')
            if os.path.exists(manifest):
                chip.schema.read_journal(manifest)
        _finalize_run(chip)

        # Summarize the run.
        chip.summary()

    # If only a manifest is specified, make a 'check_progress/' request and report results:
    elif chip_cfg:
        try:
            info = client.check_job_status()
            client._report_job_status(info)
        except Exception as e:
            chip.logger.error(f'{e}')
            return 1

    # Done
    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
