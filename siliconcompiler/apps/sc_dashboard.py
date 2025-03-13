# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler
import os
from siliconcompiler.apps._common import pick_manifest, manifest_switches, UNSET_DESIGN


def main():
    progname = "sc-dashboard"
    description = """
-----------------------------------------------------------
SC app to open a dashboard for a given manifest.

To open and allow sc-dashboard to autoload manifest:
    sc-dashboard

To open by specifying manifest:
    sc-dashboard -cfg <path to manifest>

To open by specifying design and optionally jobname:
    sc-dashboard -design <name>
    sc-dashboard -design <name> -jobname <jobname>

To specify a different port than the default:
    sc-dashboard -cfg <path to manifest> -port 10000

To include another chip object to compare to:
    sc-dashboard -cfg <path to manifest> -graph_cfg <name of manifest> <path to other manifest>
        -graph_cfg <path to other manifest> ...
-----------------------------------------------------------
"""

    # Create a base chip class.
    chip = siliconcompiler.Chip(UNSET_DESIGN)

    dashboard_arguments = {
        "-port": {'type': int,
                  'help': 'port to open the dashboard app on',
                  'metavar': '<port>',
                  'sc_print': False},
        "-graph_cfg": {'type': str,
                       'nargs': '+',
                       'action': 'append',
                       'help': 'chip name - optional, path to chip manifest (json)',
                       'metavar': '<[manifest name, manifest path>',
                       'sc_print': False}
    }

    try:
        switches = chip.create_cmdline(
            progname,
            switchlist=[*manifest_switches(),
                        '-loglevel'],
            description=description,
            additional_args=dashboard_arguments)
    except Exception as e:
        chip.logger.error(e)
        return 1

    if not chip.get('option', 'cfg'):
        manifest = pick_manifest(chip)

        if manifest:
            chip.logger.info(f'Loading manifest: {manifest}')
            chip.read_manifest(manifest)
    else:
        manifest = chip.get('option', 'cfg')

    # Error checking
    design = chip.get('design')
    if design == UNSET_DESIGN:
        chip.logger.error('Design not loaded')
        return 1

    if not manifest:
        chip.logger.error('Unable to determine job manifest')
        return 2

    graph_chips = []
    if switches['graph_cfg']:
        for i, name_and_file_path in enumerate(switches['graph_cfg']):
            args = len(name_and_file_path)
            if args == 0:
                continue
            elif args == 1:
                name = f'cfg{i}'
                file_path = name_and_file_path[0]
            elif args == 2:
                name = name_and_file_path[0]
                file_path = name_and_file_path[1]
            else:
                raise ValueError(('graph_cfg accepts a max of 2 values, you supplied'
                                  f' {args} in "-graph_cfg {name_and_file_path}"'))
            if not os.path.isfile(file_path):
                raise ValueError(f'not a valid file path: {file_path}')
            graph_chip = siliconcompiler.core.Chip(design='')
            graph_chip.read_manifest(file_path)
            graph_chips.append({
                'chip': graph_chip,
                'name': name,
                'cfg_path': os.path.abspath(file_path)
            })

    chip.dashboard(wait=True, port=switches['port'], graph_chips=graph_chips)

    return 0


#########################
if __name__ == "__main__":
    sys.exit(main())
