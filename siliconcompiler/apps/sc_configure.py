# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import sys
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

    # If a command-line argument is passed in, use that as a public server address.
    if len(sys.argv) > 1:
        print(f'Creating remote configuration file for public server: {sys.argv[1]}')
        if default_server_name in sys.argv[1] and not confirm_dialog(tos_str):
            return
        with open(cfg_file, 'w') as f:
            f.write('{"address": "%s"}'%(sys.argv[1]))
        return

    # If no arguments were passed in, interactively request credentials from the user.
    srv_addr = input('Remote server address:\n').replace(" ","")
    username = input('Remote username (leave blank for public servers):\n').replace(" ","")
    user_pass = input('Remote password (leave blank for public servers):\n').replace(" ","")

    if default_server_name in srv_addr and not confirm_dialog(tos_str):
        return

    # Save the values to the target config file in JSON format.
    with open(cfg_file, 'w') as f:
        f.write('''\
{
  "address": "%s",
  "username": "%s",
  "password": "%s"
}'''%(srv_addr, username, user_pass))

    # Let the user know that we finished successfully.
    print(f'Remote configuration saved to: {cfg_file}')

#########################
if __name__ == "__main__":
    sys.exit(main())
