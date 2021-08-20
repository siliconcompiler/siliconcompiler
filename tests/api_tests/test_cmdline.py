# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler

def main():
    progname = "sc-echo"
    chip = siliconcompiler.Chip(loglevel="DEBUG")
    chip.cmdline(progname,
                 switchlist=['source', 'cfg'],
                 description="""
                 --------------------------------------------------------------
                 Restricted SC app that accepts one or more json based cfg files
                 as inputs and executes the SC run() method.
                 """)

    #Error checking
    if not chip.get('source'):
        print(progname+": error: the following arguments are required: source")
        sys.exit()
    else:
        chip.writecfg("sc_manifest.json")

#########################
if __name__ == "__main__":
    sys.exit(main())
