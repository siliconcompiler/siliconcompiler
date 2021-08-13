# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

#Standard Modules
import sys
import logging
import os
import re
import json
import sys
import uuid
import pyfiglet
import importlib.resources
from multiprocessing import Process

#Shorten siliconcompiler as sc
import siliconcompiler
from siliconcompiler.schema import schema_cfg
from siliconcompiler.schema import schema_path
from siliconcompiler.client import fetch_results
from siliconcompiler.client import client_decrypt
from siliconcompiler.client import client_encrypt
from siliconcompiler.client import remote_preprocess
from siliconcompiler.client import remote_run
from siliconcompiler.core   import get_permutations

###########################
def main():

    # Create a base chip class.
    chip = siliconcompiler.Chip("root")

    # Silly Banner
    ascii_banner = pyfiglet.figlet_format("Silicon Compiler")
    print(ascii_banner)

    # Print out SC project authors
    authors = []
    authorfile = schema_path("AUTHORS")
    f = open(authorfile, "r")
    for line in f:
        name = re.match(r'^(\w+\s+\w+)',line)
        if name:
            authors.append(name.group(1))
    print("Authors:",", ".join(authors),"\n")
    print("-"*80)

    # Read command-line inputs and generate Chip objects to run the flow on.
    chip.cmdline()

    #Creating hashes for all sourced files
    chip.hash()

    # Perform preprocessing for remote jobs, if necessary.
    if chip.get('remote', 'addr'):
        remote_preprocess(chip)
    elif 'decrypt_key' in chip.status:
        client_decrypt(chip)

    # Run flow
    chip.run()

    # For remote jobs, fetch results.
    if chip.get('remote', 'addr'):
        fetch_results(chip)

    # Print Job Summary
    chip.summary()

    # Show job if set
    if (chip.error < 1) and (chip.get('show')):
        chip.show()

    # For local encrypted jobs, re-encrypt and delete the decrypted data.
    if 'decrypt_key' in chip.status:
        client_encrypt(chip)

#########################
if __name__ == "__main__":

    sys.exit(main())
