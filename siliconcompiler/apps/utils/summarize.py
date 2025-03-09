# Copyright 2024 Silicon Compiler Authors. All Rights Reserved.

# Standard Modules
import sys

import siliconcompiler
from siliconcompiler.apps._common import UNSET_DESIGN
from siliconcompiler import SiliconCompilerError


###########################
def main():
    progname = "summarize"
    description = """
    ------------------------------------------------------------
    Utility script to print job summary from a manifest
    ------------------------------------------------------------
    """
    # Create a base chip class.
    chip = siliconcompiler.Chip(UNSET_DESIGN)

    # Read command-line inputs and generate Chip objects to run the flow on.
    try:
        chip.create_cmdline(progname,
                            description=description,
                            switchlist=['-cfg',
                                        '-loglevel'])
    except SiliconCompilerError:
        return 1
    except Exception as e:
        chip.logger.error(e)
        return 1

    design = chip.get('design')
    if design == UNSET_DESIGN:
        chip.logger.error('Design not loaded')
        return 1

    # Print Job Summary
    chip.summary()

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
