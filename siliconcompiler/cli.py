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

###########################
def main():

    # Create a base chip class.
    chip = siliconcompiler.Chip()

    # Read command-line inputs and generate Chip objects to run the flow on.
    chip.cmdline("sc",
                 description="""
                 --------------------------------------------------------------
                 SiliconCompiler is an open source Python based hardware
                 compiler project that aims to fully automate the translation
                 of high level source code into manufacturable hardware. The program
                 is a command line utility app around the SC APi and schema that
                 calls executes the following functions in sequence:

                 1. target(), if defined

                 2. hash()

                 3. run()

                 4. summary()

                 5. show(), if defined

                 Website: https://www.siliconcompiler.com
                 Documentation: https://www.siliconcompiler.com/docs
                 Community: https://www.siliconcompiler.com/community
                 """)

    #Creating hashes for all sourced files
    chip.hash()

    # Run flow
    chip.run()

    # Print Job Summary
    chip.summary()

    # Show job if set
    # if (chip.error < 1) and (chip.get('show')):
    #   chip.show()

#########################
if __name__ == "__main__":

    sys.exit(main())
