# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler

def main():
    progname = "sc-check"
    chip = siliconcompiler.Chip()
    chip.cmdline(progname,
                 switchlist=['cfg', 'loglevel'],
                 description="""
                 --------------------------------------------------------------
                 Restricted SC app that accepts one or more json based cfg files
                 as inputs and executes the SC check() method.
                 """)

    #Error checking
    if not chip.get('cfg'):
        print(progname+": error: the following arguments are required: -cfg")
        sys.exit()
    else:
        error = chip.check()

    return error

#########################
if __name__ == "__main__":
    sys.exit(main())
