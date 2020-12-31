# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

#Standard Modules
import sys

#Shorten siliconcompiler as sc
import siliconcompiler as sc

#Silicon Compiler Modules
from siliconcompiler.core import init
from siliconcompiler.core import readenv
from siliconcompiler.core import cmdline
from siliconcompiler.core import run

###########################
def main(args=None):
    
    sc_args            = {}
    sc_args['default'] = sc.init()                       # defines dictionary
    sc_args['env']     = sc.readenv(sc_args['default'])  # env variables
    sc_args['cli']     = sc.cmdline(sc_args['default'])      # command line args
    sc_args['files']   = {}

    sc.run(sc_args,"cli")

#########################
if __name__ == "__main__":    
    sys.exit(main())
