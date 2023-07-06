# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler


def main():
    progname = "sc-dashboard"
    description = """
-----------------------------------------------------------
SC app to open a dashboard for a given manifest.

To open:
    sc-dashboard -cfg <path to manifest>

To specify a different port than the default:
    sc-dashboard -cfg <path to manifest> -port 10000
-----------------------------------------------------------
"""

    # TODO: this is a hack to get around design name requirement: since legal
    # design names probably can't contain spaces, we can detect if it is unset.
    UNSET_DESIGN = '  unset  '

    # Create a base chip class.
    chip = siliconcompiler.Chip(UNSET_DESIGN)

    dashboard_arguments = {
        "-port": {'type': int,
                  'help': 'port to open the dashboard app on',
                  'metavar': '<port>'}
    }

    switches = chip.create_cmdline(
        progname,
        switchlist=['-loglevel',
                    '-cfg'],
        description=description,
        additional_args=dashboard_arguments)

    # Error checking
    design = chip.get('design')
    if design == UNSET_DESIGN:
        chip.logger.error('Design not loaded')
        return 1

    chip._dashboard(wait=True, port=switches['port'])

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
