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
------------------------------------------------------------
SiliconCompiler is an open source Python based meta compiler
project that aims to fully automate the translation of high
level source code into manufacturable hardware. This program
is a command line utility app around the SC API/schema that
executes the following operations in sequence:

1. load setup files through target(),
2. load settings from json files provided with -cfg switch
3. override settings using other switches
4. run()
5. summary()

**More Information:**
Website:       https://www.siliconcompiler.com
Documentation: https://www.siliconcompiler.com/docs
Community:     https://www.siliconcompiler.com/community
------------------------------------------------------------
""")

    # Run flow
    chip.run()

    # Print Job Summary
    chip.summary()

#########################
if __name__ == "__main__":

    sys.exit(main())
