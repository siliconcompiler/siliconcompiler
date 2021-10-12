# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler

def main():
    progname = "sc-run"
    chip = siliconcompiler.Chip()
    switchlist = ['cfg',
                  'loglevel',
                  'checkonly',
                  'relax',
                  'quiet',
                  'version']
    description = """
    -----------------------------------------------------------
    Restricted SC app that accepts one or more json based cfg files
    as inputs and executes the SC run() method.
    -----------------------------------------------------------
    """
    chip.create_cmdline(progname,
                        switchlist=switchlist,
                        description=description)


    #Error checking
    if not chip.get('cfg'):
        print(progname+": error: the following arguments are required: -cfg")
        sys.exit()
    else:
        chip.run()

#########################
if __name__ == "__main__":
    sys.exit(main())
