#!/usr/bin/env python3

import importlib
import os
import sys
import siliconcompiler

from siliconcompiler.floorplan import Floorplan

def main():
    progname = "sc-floorplan"
    description = """
    --------------------------------------------------------------
    Restricted SC app that accepts one ore more json based cfg
    files and the path to an SC floorplan via the source argument.
    """

    chip = siliconcompiler.Chip()

    chip.create_cmdline(progname,
                        switchlist=['source', 'cfg', 'loglevel', 'design', 'target'],
                        description=description)

    #Error checking
    if not chip.get('source') or not chip.get('design'):
        print(progname+": error: the following arguments are required: source, design")
        sys.exit()

    floorplan_file = chip.get('source')[0]

    fp = Floorplan(chip)

    # Import user's floorplan file, call setup_floorplan to set up their
    # floorplan, and save it as a DEF
    mod_name = os.path.splitext(os.path.basename(floorplan_file))[0]
    mod_spec = importlib.util.spec_from_file_location(mod_name, floorplan_file)
    module = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(module)
    setup_floorplan = getattr(module, "setup_floorplan")

    setup_floorplan(fp)

    topmodule = chip.get('design')
    fp.write_def(f'{topmodule}.def')
    fp.write_lef(f'{topmodule}.lef')

    # TODO: once show is complete, perhaps have it called automatically (optionally?)

#########################
if __name__ == "__main__":
    sys.exit(main())
