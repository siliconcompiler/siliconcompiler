# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler


def main():
    progname = "sc-run"
    chip = siliconcompiler.Chip(progname)
    switchlist = ['-cfg',
                  '-loglevel',
                  '-relax',
                  '-quiet']
    description = """
    -----------------------------------------------------------
    Restricted SC app that accepts one or more json based cfg files
    as inputs and executes the SC run() method.
    -----------------------------------------------------------
    """
    chip.create_cmdline(progname,
                        switchlist=switchlist,
                        description=description)

    # Error checking
    if not chip.get('cfg'):
        print(f"{progname} error: the following arguments are required: -cfg")
        return 1
    else:
        chip.run()

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
