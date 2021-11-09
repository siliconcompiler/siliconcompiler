# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import sys
import siliconcompiler
from pathlib import Path

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

    cfg_dir = os.path.join(Path.home(), '.siliconcompiler')
    cfg_file = os.path.join(cfg_dir, '.remote_config')
    if not os.path.isdir(cfg_dir):
        os.makedirs(cfg_dir)
    if os.path.isfile(cfg_file):
        overwrite = False
        while not overwrite:
            oin = input('Overwrite existing remote configuration? (y/N)')
            if (not oin) or (oin == 'n') or (on == 'N'):
                print('Exiting.')
                return
            elif (oin == 'y') or (oin == 'Y'):
                overwrite = True
    srv_addr = input('Remote server address: ')
    username = input('Remote username: ')
    user_pass = input('Remote password: ')
    with open(cfg_file, 'w') as f:
        f.write('''\
{
  "address": "%s",
  "username": "%s",
  "password": "%s"
}'''%(srv_addr, username, user_pass))
    print('Configuration saved.')

#########################
if __name__ == "__main__":
    sys.exit(main())
