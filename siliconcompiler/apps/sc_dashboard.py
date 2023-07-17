# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler
import os


def main():
    progname = "sc-dashboard"
    description = """
-----------------------------------------------------------
SC app to open a dashboard for a given manifest.

To open:
    sc-dashboard -cfg <path to manifest>

To specify a different port than the default:
    sc-dashboard -cfg <path to manifest> -port 10000

To include another chip object to compare to:
    sc-dashboard -cfg <path to manifest> -comparison_chip <path to other manifest> <path to another manifest>
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
                  'metavar': '<port>'},
        "-comparison_chip": {'type': str,
                             'nargs': '+',
                             'help': 'chip name, path to chip manifest (json)',
                             'metavar': '<comparison_chip>'}
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

    comparison_chips = []
    for i, file_path in enumerate(switches['comparison_chip']):
        if not os.path.isfile(file_path):
            raise (f'not a valid file path : {file_path}')
        comparison_chip = siliconcompiler.core.Chip(design='')
        comparison_chip.read_manifest(file_path)
        comparison_chips.append({'chip': comparison_chip, 'name': f'chip{i}'})

    chip._dashboard(wait=True, port=switches['port'],
                    comparison_chips=comparison_chips)

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
