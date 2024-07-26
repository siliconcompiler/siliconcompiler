# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

# Standard Modules
import os
import sys

import siliconcompiler
from siliconcompiler.utils import get_default_iomap
from siliconcompiler.targets import skywater130_demo
from siliconcompiler import SiliconCompilerError


###########################
def main():
    progname = "sc"
    description = """
    ------------------------------------------------------------
    SiliconCompiler is an open source compiler framework that
    aims to enable automated translation from source code to
    silicon.

    The sc program includes the following steps.

    1. Read command line arguments
    2. If not set, 'design' is set to base of first source file.
    3. If not set, 'target' is set to 'skywater130_demo'.
    4. Run compilation
    5. Display summary

    Sources: https://github.com/siliconcompiler/siliconcompiler
    ------------------------------------------------------------
    """
    # TODO: this is a hack to get around design name requirement: since legal
    # design names probably can't contain spaces, we can detect if it is unset.
    UNSET_DESIGN = '  unset  '

    # Create a base chip class.
    chip = siliconcompiler.Chip(UNSET_DESIGN)

    # Read command-line inputs and generate Chip objects to run the flow on.
    try:
        chip.create_cmdline(progname,
                            description=description,
                            input_map=get_default_iomap())
    except Exception as e:
        chip.logger.error(e)
        return 1

    # Set design if none specified
    if chip.get('design') == UNSET_DESIGN:
        topfile = None
        for sourceset in ('rtl', 'hll'):
            for filetype in chip.getkeys('input', sourceset):
                all_vals = chip.schema._getvals('input', sourceset, filetype)
                if all_vals:
                    # just look at first value
                    sources, _, _ = all_vals[0]
                    # grab first source
                    topfile = sources[0]
                    break
            if topfile:
                break

        if not topfile:
            chip.logger.error('Invalid arguments: either specify -design or provide sources.')
            return 1

        topmodule = os.path.splitext(os.path.basename(topfile))[0]
        chip.set('design', topmodule)

    # Set demo target if none specified
    if not chip.get('option', 'target'):
        chip.load_target(skywater130_demo)

    try:
        # Run flow
        chip.run()

        # Print Job Summary
        chip.summary()
    except SiliconCompilerError:
        return 1
    except Exception as e:
        chip.logger.error(e)
        return 1

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
