# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import json
import os
import sys
import argparse

from siliconcompiler.utils import default_credentials_file

from siliconcompiler import Chip
from siliconcompiler.remote.client import remote_ping


def main():
    progname = "sc-ping"
    description = """
    -----------------------------------------------------------
    SC app that loads a remote configuration file, and pings the server
    for user account information.
    -----------------------------------------------------------
    """

    # Argument Parser
    parser = argparse.ArgumentParser(prog=progname,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=description)

    parser.add_argument('credential', nargs='?', default=default_credentials_file())

    # Parsing args and converting to dict
    cmdargs = vars(parser.parse_args())
    cfg_file = cmdargs['credential']

    # Check the configuration.
    if not os.path.isfile(cfg_file):
        print('Error: Remote configuration was not found. Please run "sc-configure".')
        return 1

    try:
        with open(cfg_file, 'r') as cfgf:
            remote_cfg = json.loads(cfgf.read())
    except Exception:
        print('Error reading remote configuration file.')
        return 1

    # Create the chip object and generate the request
    chip = Chip('ping')
    chip.status['remote_cfg'] = remote_cfg

    # Make the request and print its response.
    try:
        remote_ping(chip)
    except Exception:
        print('Error fetching user information from the remote server.')
        return 1

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
