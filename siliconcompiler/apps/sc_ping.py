# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import json
import os
import requests
import sys
import argparse

from siliconcompiler.utils import default_credentials_file

from siliconcompiler import Chip
from siliconcompiler.client import get_base_url


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
    request_url = get_base_url(chip) + '/check_user/'
    post_params = {}
    if 'username' in remote_cfg:
        post_params['username'] = remote_cfg['username']
    if 'password' in remote_cfg:
        post_params['key'] = remote_cfg['password']

    # Make the request and print its response.
    try:
        redirect_url = request_url
        while redirect_url:
            resp = requests.post(redirect_url,
                                 data=json.dumps(post_params),
                                 allow_redirects=False)
            if resp.status_code == 302:
                redirect_url = resp.headers['Location']
            else:
                redirect_url = None
        # Get the JSON response values.
        user_info = resp.json()
        if (resp.status_code != 200) or \
           ('compute_time' not in user_info) or \
           ('bandwidth_kb' not in user_info):
            print('Error fetching user information from the remote server.')
            return 1

        # Print the user's account info, and return.
        print(f'User {remote_cfg["username"]}:')
        print(f'  Remaining compute time: {(user_info["compute_time"]/60.0):.2f} minutes')
        print(f'  Remaining results bandwidth: {user_info["bandwidth_kb"]} KiB')
        return 0
    except Exception:
        print('Error fetching user information from the remote server.')
        return 1


#########################
if __name__ == "__main__":
    sys.exit(main())
