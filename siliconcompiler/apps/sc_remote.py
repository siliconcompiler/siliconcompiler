# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import copy
import json
import os
import sys

from siliconcompiler import Chip
from siliconcompiler._metadata import default_server
from siliconcompiler.remote.client import (cancel_job, check_progress, delete_job,
                                           remote_ping, remote_run_loop)
from siliconcompiler.utils import default_credentials_file


def main():
    progname = "sc-remote"
    description = """
    -----------------------------------------------------------
    SC app that provides an entry point to common remote / server
    interactions. Can be used to:
    * Check software versions on the server (no flags)
    * Check an ongoing job's progress (-jobid)
    * Cancel an ongoing job (-jobid + -cancel)
    * Re-attach SC client to an ongoing job (-jobid + -attach)
    -----------------------------------------------------------
    """

    # Argument Parser
    progname = 'sc_remote'
    chip = Chip(progname)
    switchlist = ['-cfg', '-credentials']
    extra_args = {
        '-jobid': {'required': False},
        '-reconnect': {'action': 'store_true', 'required': False},
        '-cancel': {'action': 'store_true', 'required': False},
        '-delete': {'action': 'store_true', 'required': False},
    }
    args = chip.create_cmdline(progname,
                               switchlist=switchlist,
                               additional_args=extra_args,
                               description=description)

    # Sanity checks.
    if (args['reconnect'] and (args['cancel'] or args['delete'])):
        chip.logger.error('Error: -reconnect is mutually exclusive to -cancel and -delete')
        return 1
    elif (args['cancel'] and (args['reconnect'] or args['delete'])):
        chip.logger.error('Error: -cancel is mutually exclusive to -reconnect and -delete')
        return 1
    elif ((args['reconnect'] or args['cancel'] or args['delete']) and not args['jobid']):
        chip.logger.error('Error: -jobid is required for -reconnect, -cancel, and -delete')
        return 1
    elif (args['reconnect'] and not chip.get('option', 'cfg')):
        chip.logger.error("Error: -cfg is required for -reconnect. Recommended value is "
                          "the post-import manifest in the job's original build directory.")
        return 1

    # Read in credentials from file, if specified and available.
    # Otherwise, use the default server address.
    if not chip.get('option', 'credentials'):
        chip.set('option', 'credentials', default_credentials_file())
    if os.path.isfile(chip.get('option', 'credentials')):
        with open(chip.get('option', 'credentials'), 'r') as cfgf:
            try:
                remote_cfg = json.loads(cfgf.read())
                chip.logger.warning(remote_cfg)
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
    chip.status['jobhash'] = args['jobid']
    remote_ping(chip)

    # If the -cancel flag is specified, cancel the job.
    if args['cancel']:
        cancel_job(chip)

    # If the -delete flag is specified, delete the job.
    elif args['delete']:
        delete_job(chip)

    # If the -reconnect flag is specified, re-enter the client flow
    # in its "check_progress/ until job is done" loop.
    elif args['reconnect']:
        # TODO: Will require optional '-cfg' argument, we can't reconnect
        # without the job's manifest. If we update the server to return the
        # design name in the 'check_progress/' response, we could instead accept
        # optional '-builddir' and '-jobname' arguments, then get the design
        # and node names from a call to 'check_progress/'.
        # Also, total runtime value will be incorrect; maybe we can have the
        # server return the job's "created_at" time in the check_progress/ response.
        chip.read_manifest(chip.get('option', 'cfg')[0])
        # Remove entry steps from the steplist, so that they are not fetched from the remote.
        remote_steps = chip.list_steps()
        environment = copy.deepcopy(os.environ)
        entry_nodes = chip._get_flowgraph_entry_nodes(flow=chip.get('option', 'flow'))
        for node in entry_nodes:
            remote_steps.remove(node[0])
        chip.set('option', 'steplist', remote_steps)
        # Enter the remote run loop.
        remote_run_loop(chip)
        # Summarize the run.
        chip._finalize_run(chip.list_steps(), environment)
        chip.summary()

    # If only a job ID is specified, make a 'check_progress/' request and report results:
    elif args['jobid']:
        check_progress(chip)

    # Done
    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
