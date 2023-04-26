# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import sys
import json
from pathlib import Path
from urllib.parse import urlparse

from siliconcompiler._metadata import default_server

tos_str = '''Please review the SiliconCompiler cloud beta's terms of service:

https://www.siliconcompiler.com/terms-of-service

In particular, please ensure that you have the right to distribute any IP which is contained in designs that you upload to the service. This public service, provided by SiliconCompiler, is not intended to process proprietary IP.
'''

def confirm_dialog(message):
    confirmed = False
    while not confirmed:
        oin = input(f'{message} y/N: ')
        if (not oin) or (oin == 'n') or (oin == 'N'):
            print('Exiting.')
            break
        elif (oin == 'y') or (oin == 'Y'):
            confirmed = True
    return confirmed

def main():
    progname = "sc-configure"
    switchlist = []
    description = """
    -----------------------------------------------------------
    SC app that saves a remote configuration file for use with
    the '-remote' flag. It prompts the user for information
    about the account and remote server.
    -----------------------------------------------------------
    """

    default_server_name = urlparse(default_server).hostname

    # Return early and print a help string if necessary.
    if (len(sys.argv) > 1) and \
       ((sys.argv[1] == '--help') or (sys.argv[1] == '-h')):
        print('Usage: sc-configure')
        print('Generates the remote configuration file.')
        sys.exit(0)

    # Find the config file/directory path.
    cfg_dir = os.path.join(Path.home(), '.sc')
    cfg_file = os.path.join(cfg_dir, 'credentials')
    # Create directory if it doesn't exist.
    if not os.path.isdir(cfg_dir):
        os.makedirs(cfg_dir)

    # If an existing config file exists, prompt the user to overwrite it.
    if os.path.isfile(cfg_file):
        if not confirm_dialog('Overwrite existing remote configuration?'):
            return

    config = {}

    # If a command-line argument is passed in, use that as a public server address.
    interactive = len(sys.argv) <= 1
    if not interactive:
        print(f'Creating remote configuration file for public server: {sys.argv[1]}')
        srv_addr = sys.argv[1]
    else:
        # If no arguments were passed in, interactively request credentials from the user.
        srv_addr = input('Remote server address:\n').replace(" ","")

    server = urlparse(srv_addr)
    has_scheme = True
    if not server.hostname:
        # fake add a scheme to the url
        has_scheme = False
        server = urlparse('https://' + srv_addr)
    if not server.hostname:
        print(f'Invalid address provided: {srv_addr}')
        return

    if has_scheme:
        config['address'] = f'{server.scheme}://{server.hostname}'
    else:
        config['address'] = server.hostname

    public_server = default_server_name in srv_addr
    if public_server and not confirm_dialog(tos_str):
        return

    if server.port is not None:
        config['port'] = server.port

    if not public_server and interactive:
        username = server.username
        if not username:
            username = input('Remote username:\n').replace(" ","")
        user_pass = server.password
        if not user_pass:
            user_pass = input('Remote password:\n').replace(" ","")

        if username:
            config['username'] = username
        if user_pass:
            config['password'] = user_pass

    # Save the values to the target config file in JSON format.
    with open(cfg_file, 'w') as f:
        f.write(json.dumps(config, indent=4))

    # Let the user know that we finished successfully.
    print(f'Remote configuration saved to: {cfg_file}')

#########################
if __name__ == "__main__":
    sys.exit(main())
