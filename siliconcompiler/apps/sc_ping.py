# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import json
import os
import requests
import sys

from pathlib import Path
from siliconcompiler import Chip
from siliconcompiler.client import get_base_url

def main():
    progname = "sc-ping"
    switchlist = []
    description = """
    -----------------------------------------------------------
    SC app that loads a remote configuration file, and pings the server
    for user account information.
    -----------------------------------------------------------
    """

    # Return early and print a help string if necessary.
    if (len(sys.argv) > 1) and \
       ((sys.argv[1] == '--help') or (sys.argv[1] == '-h')):
        print('Usage: sc-ping')
        print('Prints remote user account information.')
        print('Requires a remote configuration file (run "sc-configure")')
        sys.exit(0)

    # Find the config file/directory path.
    cfg_dir = os.path.join(Path.home(), '.sc')
    cfg_file = os.path.join(cfg_dir, 'credentials')

    # Check the configuration.
    if not os.path.isfile(cfg_file):
        print('Error: Remote configuration was not found. Please run "sc-configure".')
        sys.exit(1)
    try:
        with open(cfg_file, 'r') as cfgf:
            remote_cfg = json.loads(cfgf.read())
        if (not 'username' in remote_cfg) or \
           (not 'password' in remote_cfg) or \
           (not 'address' in remote_cfg):
            print('Error reading remote configuration file.')
            sys.exit(1)
    except:
        print('Error reading remote configuration file.')
        sys.exit(1)

    # Create the chip object and generate the request
    chip = Chip()
    chip.status['remote_cfg'] = remote_cfg
    request_url = get_base_url(chip) + '/check_user/'
    post_params = {
        'username': remote_cfg['username'],
        'key': remote_cfg['password'],
    }

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
           (not 'compute_time' in user_info) or \
           (not 'bandwidth_kb' in user_info):
            print('Error fetching user information from the remote server.')
            sys.exit(1)

        # Print the user's account info, and return.
        print(f'User {remote_cfg["username"]} validated successfully!')
        print(f'  Remaining compute time: {(user_info["compute_time"]/60.0):.2f} minutes')
        print(f'  Remaining results bandwidth: {user_info["bandwidth_kb"]} KiB')
        return
    except:
        print('Error fetching user information from the remote server.')
        sys.exit(1)

#########################
if __name__ == "__main__":
    sys.exit(main())
