# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import sys
import json
import argparse
from urllib.parse import urlparse

from siliconcompiler._metadata import default_server
from siliconcompiler.utils import default_credentials_file

tos_str = '''Please review the SiliconCompiler cloud beta's terms of service:

https://www.siliconcompiler.com/terms-of-service

In particular, please ensure that you have the right to distribute any IP
which is contained in designs that you upload to the service. This public
service, provided by SiliconCompiler, is not intended to process proprietary IP.
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
    description = """
    -----------------------------------------------------------
    SC app that saves a remote configuration file for use with
    the '-remote' flag. It prompts the user for information
    about the account and remote server.
    -----------------------------------------------------------
    """

    # Argument Parser
    parser = argparse.ArgumentParser(prog=progname,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=description)

    parser.add_argument('-file', metavar='<file>', default=default_credentials_file(),
                        help='Path to credentials file')
    parser.add_argument('server', nargs='?',
                        help='URL to a server')

    # Parsing args and converting to dict
    cmdargs = vars(parser.parse_args())

    default_server_name = urlparse(default_server).hostname

    # Find the config file/directory path.
    cfg_file = cmdargs['file']
    cfg_dir = os.path.dirname(cfg_file)

    # Create directory if it doesn't exist.
    if not os.path.isdir(cfg_dir):
        os.makedirs(cfg_dir)

    # If an existing config file exists, prompt the user to overwrite it.
    if os.path.isfile(cfg_file):
        if not confirm_dialog('Overwrite existing remote configuration?'):
            return 0

    config = {}

    # If a command-line argument is passed in, use that as a public server address.
    if cmdargs['server']:
        srv_addr = cmdargs['server']
        print(f'Creating remote configuration file for public server: {srv_addr}')
    else:
        # If no arguments were passed in, interactively request credentials from the user.
        srv_addr = input('Remote server address:\n').replace(" ", "")

    server = urlparse(srv_addr)
    has_scheme = True
    if not server.hostname:
        # fake add a scheme to the url
        has_scheme = False
        server = urlparse('https://' + srv_addr)
    if not server.hostname:
        print(f'Invalid address provided: {srv_addr}')
        return 1

    if has_scheme:
        config['address'] = f'{server.scheme}://{server.hostname}'
    else:
        config['address'] = server.hostname

    public_server = default_server_name in srv_addr
    if public_server and not confirm_dialog(tos_str):
        return

    if server.port is not None:
        config['port'] = server.port

    if not public_server and not cmdargs['server']:
        username = server.username
        if not username:
            username = input('Remote username:\n').replace(" ", "")
        user_pass = server.password
        if not user_pass:
            user_pass = input('Remote password:\n').replace(" ", "")

        if username:
            config['username'] = username
        if user_pass:
            config['password'] = user_pass

    # Save the values to the target config file in JSON format.
    with open(cfg_file, 'w') as f:
        f.write(json.dumps(config, indent=4))

    # Let the user know that we finished successfully.
    print(f'Remote configuration saved to: {cfg_file}')

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
