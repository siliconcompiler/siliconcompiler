# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import argparse
import json
import os

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
    parser = argparse.ArgumentParser(prog=progname,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=description)
    parser.add_argument('-jobid', required=False)
    parser.add_argument('-reconnect', action='store_true', required=False)
    parser.add_argument('-cancel', action='store_true', required=False)
    parser.add_argument('-delete', action='store_true', required=False)
    parser.add_argument('-credentials', nargs='?', default=default_credentials_file())

    args = parser.parse_args()

    # Sanity checks.
    if (args.reconnect and (args.cancel or args.delete)):
        print('Error: -reconnect is mutually exclusive to -cancel and -delete')
        return 1
    elif (args.cancel and (args.reconnect or args.delete)):
        print('Error: -cancel is mutually exclusive to -reconnect and -delete')
        return 1
    elif (args.delete and (args.reconnect or args.cancel)):
        print('Error: -delete is mutually exclusive to -reconnect and -cancel')
        return 1
    elif ((args.reconnect or args.cancel or args.delete) and not args.jobid):
        print('Error: -jobid is required for -reconnect, -cancel, and -delete')
        return 1

    # Read in credentials from file, if specified and available.
    # Otherwise, use the default server address.
    if os.path.isfile(args.credentials):
        with open(args.credentials, 'r') as cfgf:
            try:
                remote_cfg = json.loads(cfgf.read())
            except json.JSONDecodeError:
                print('Error reading remote configuration file: invalid JSON')
                return 1
    else:
        # TODO: I think this default is stored somewhere - client.py? _metadata.py?
        remote_cfg = {'address': 'https://server.siliconcompiler.com',
                      'port': '443'}

    # Main logic.
    # If no job-related options are specified, fetch and report basic info.
    # Server-side software versions:
    # TODO
    # User account info, only if authentication values are present in credentials:
    # TODO

    # If only a job ID is specified, make a 'check_progress/' request and report results:
    # TODO

    # If the -cancel flag is specified, cancel the job.
    # TODO

    # If the -delete flag is specified, delete the job.
    # TODO

    # If the -reconnect flag is specified, re-enter the client flow
    # in its "check_progress/ until job is done" loop.
    # TODO

    # Done
    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
