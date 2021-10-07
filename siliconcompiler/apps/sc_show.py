# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler

def main():
    progname = "sc-show"
    description = """
    --------------------------------------------------------------
    Restricted SC app that accepts one ore more json based cfg
    files and a source file to show using the SC show() method.
    """

    chip = siliconcompiler.Chip()
    chip.create_cmdline(progname,
                        switchlist=['source', 'cfg', 'loglevel'],
                        description=description)

    #Error checking
    if (not chip.get('source')) | (not chip.get('cfg')) :
        print(progname+": error: the following arguments are required: source,cfg")
        sys.exit()

    # sources specified in the -cfg file go first in the list, so we display the
    # last source file in the list
    source = chip.get('source')[-1]

    chip.show_file(source)

#########################
if __name__ == "__main__":
    sys.exit(main())
