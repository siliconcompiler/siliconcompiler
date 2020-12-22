#!/usr/bin/env python3
# Copyright Silicon Compiler Collection (SCC) Contributors

r"""Silicon Compiler Command Line Tool"""

import argparse
import subprocess
import re
import sys
import os
import logging
from pathlib import Path

#############################################################################
DESC = """
Description:
  scc (silicon compiler collection) generates GDSII from Verilog RTL"""

USAGE = """
Usage:
  scc [options] <input>
  scc (-h | --help)
  scc (--version)
"""

##############################################################################

def main():    
    args = parse_args() #parse arguments
    if not args:
        exit(0)
    
 
