# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler

def main():
    progname = "sc-show"
    chip = siliconcompiler.Chip()
    chip.cmdline(progname,
                 switchlist=['source', 'cfg', 'loglevel'],
                 description="""
                 --------------------------------------------------------------
                 Restricted SC app that accepts one ore more json based cfg
                 files and a source file to show using the SC show() method.
                 """)

    #Error checking
    if (not chip.get('source')) | (not chip.get('cfg')) :
        print(progname+": error: the following arguments are required: source,cfg")
        sys.exit()
    #Running show()
    chip.show(chip.get('source')[0])

#########################
if __name__ == "__main__":
    sys.exit(main())
