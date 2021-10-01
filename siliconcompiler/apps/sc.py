# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

#Standard Modules
import sys
import logging
import os
import re
import json
import sys
import uuid
import importlib.resources
from multiprocessing import Process

#Shorten siliconcompiler as sc
import siliconcompiler
import siliconcompiler.client

###########################
def main():


    progname = "sc"
    description = """
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
    """

    # Create a base chip class.
    chip = siliconcompiler.Chip()

    # Read command-line inputs and generate Chip objects to run the flow on.
    chip.create_cmdline(progname,
                        description=description)

    # Run flow
    chip.run()

    # Print Job Summary
    chip.summary()

#########################
if __name__ == "__main__":

    sys.exit(main())
