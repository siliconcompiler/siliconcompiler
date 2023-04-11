# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import argparse
import os
import sys

from siliconcompiler.crypto import encrypt_job
from siliconcompiler.crypto import decrypt_job
from siliconcompiler.crypto import decrypt_cfgfile

# Provide a way to encrypt/decrypt from the command line. (With the correct key)
# This is mostly intended to make it easier to run individual job steps in an
# HPC cluster when the data needs to be encrypted 'at rest'. It should not be
# necessary to run these steps manually in a normal workflow.
def main():
    #Argument Parser
    parser = argparse.ArgumentParser(prog='sc-crypt',
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50),
                                     prefix_chars='-+',
                                     description="Silicon Compiler Collection Encrypt / Decrypt Utility")

    # Command-line options (all required):
    parser.add_argument('-mode', required=True)
    parser.add_argument('-target', required=True)
    parser.add_argument('-key_file', required=True)

    # Parse arguments.
    cmdargs = vars(parser.parse_args())

    # Check for invalid parameters.
    if (not cmdargs['mode'] in ['encrypt', 'decrypt', 'decrypt_config']) or \
       (not os.path.exists(cmdargs['target'])) or \
       (not os.path.isfile(cmdargs['key_file'])):
        print('Error: Invalid command-line parameters.', file=sys.stderr)
        sys.exit(1)

    # Perform the encryption or decryption.
    if cmdargs['mode'] == 'encrypt':
        encrypt_job(cmdargs['target'], cmdargs['key_file'])
    elif cmdargs['mode'] == 'decrypt':
        decrypt_job(cmdargs['target'], cmdargs['key_file'])
    elif cmdargs['mode'] == 'decrypt_config':
        decrypt_cfgfile(cmdargs['target'], cmdargs['key_file'])

if __name__ == "__main__":
    main()
