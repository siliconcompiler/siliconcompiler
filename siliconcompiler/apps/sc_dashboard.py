# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler


def main():
    progname = "sc-dashboard"
    description = """
    --------------------------------------------------------------
    Restricted SC app that opens a dashboard...
    """

    # TODO: this is a hack to get around design name requirement: since legal
    # design names probably can't contain spaces, we can detect if it is unset.
    UNSET_DESIGN = '  unset  '

    # Create a base chip class.
    chip = siliconcompiler.Chip(UNSET_DESIGN)

    chip.create_cmdline(
        progname,
        switchlist=['-loglevel',
                    '-cfg'],
        description=description)

    # Error checking
    design = chip.get('design')
    if design == UNSET_DESIGN:
        chip.logger.error('Design not loaded')
        return 1

    chip._dashboard(wait=True)

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
