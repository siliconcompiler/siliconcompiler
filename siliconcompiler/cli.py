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
    base_chip = siliconcompiler.Chip()

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
    chips = base_chip.cmdline()

    # Check and lock each permutation.
    for chip in chips:
        #Checks settings and fills in missing values
        chip.check()

        #Creating hashes for all sourced files
        chip.hash()

    # Perform preprocessing for remote jobs, if necessary.
    if len(chips[-1].get('remote', 'addr')) > 0:
        remote_preprocess(chips)

    # Perform decryption, if necessary.
    elif 'decrypt_key' in chips[-1].status:
        for chip in chips:
            client_decrypt(chip)

    # Run each job in its own thread.
    chip_procs = []
    for chip in chips:
        # Running compilation pipeline
        new_proc = Process(target=chip.run)
        new_proc.start()
        chip_procs.append(new_proc)

    # Wait for threads to complete.
    for proc in chip_procs:
        proc.join()

    # For remote jobs, fetch results.
    if len(chips[-1].get('remote', 'addr')) > 0:
        fetch_results(chips)

    # Print Job Summary
    for chip in chips:
        if chip.error < 1:
            chip.summary()

    # For local encrypted jobs, re-encrypt and delete the decrypted data.
    if 'decrypt_key' in chips[-1].status:
        for chip in chips:
            client_encrypt(chip)


#########################
if __name__ == "__main__":

    sys.exit(main())
