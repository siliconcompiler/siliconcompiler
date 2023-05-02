# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import os
import glob
import siliconcompiler
from siliconcompiler.utils import get_default_iomap
from siliconcompiler.targets.utils import set_common_showtools


def _get_manifest(dirname):
    # pkg.json file may have a different name from the design due to the entrypoint
    manifest = glob.glob(os.path.join(dirname, '*.pkg.json'))
    if manifest:
        manifest = manifest[0]
    else:
        manifest = None

    if not manifest or not os.path.isfile(manifest):
        return None
    return manifest


def main():
    progname = "sc-show"
    description = """
    --------------------------------------------------------------
    Restricted SC app that displays the layout of a design
    based on a file provided or tries to display the final
    layout based on loading the json manifest from:
    build/<design>/job0/<design>.pkg.json

    Examples:

    sc-show -design adder
    (displays build/job0/adder/export/0/outputs/adder.gds)

    sc-show build/job0/adder/route/1/outputs/adder.def
    (displays build/job0/adder/route/1/outputs/adder.def)

    """

    # TODO: this is a hack to get around design name requirement: since legal
    # design names probably can't contain spaces, we can detect if it is unset.
    UNSET_DESIGN = '  unset  '

    # Create a base chip class.
    chip = siliconcompiler.Chip(UNSET_DESIGN)

    # Fill input map with default mapping only for showable files
    input_map = {}
    default_input_map = get_default_iomap()
    show_chip = siliconcompiler.Chip('show-tools')
    set_common_showtools(show_chip)
    for ext in show_chip.getkeys('option', 'showtool'):
        if ext in default_input_map:
            input_map[ext] = default_input_map[ext]

    chip.create_cmdline(progname,
                        switchlist=['-design', '-input', '-loglevel', '-cfg'],
                        description=description,
                        input_map=input_map)

    # Error checking
    design = chip.get('design')
    design_set = design != UNSET_DESIGN

    input_mode = None
    if 'layout' in chip.getkeys('input'):
        for mode in chip.getkeys('input', 'layout'):
            if chip.schema._getvals('input', 'layout', mode):
                input_mode = mode
                break

    if not (design_set or input_mode):
        chip.logger.error('Nothing to load: please define a target with -cfg, -design, and/or -input.')
        sys.exit(1)

    filename = None
    if input_mode:
        all_vals = chip.schema._getvals('input', 'layout', input_mode)
        # Get first value, corresponds to a list of files
        val, _, _ = all_vals[0]
        # Get last item in list
        filename = val[-1]

    if (filename is not None) and (not chip.get('option', 'cfg')):
        # only autoload manifest if user doesn't supply manually
        manifest = _get_manifest(os.path.dirname(filename))
        if not manifest:
            design = os.path.splitext(os.path.basename(filename))[0]
            chip.logger.error(f'Unable to automatically find manifest for design {design}. '
                              'Please provide a manifest explicitly using -cfg.')
            sys.exit(1)
        chip.read_manifest(manifest)
    elif not chip.get('option', 'cfg'):
        manifest = _get_manifest(chip._getworkdir())
        if not manifest:
            chip.logger.warning('Could not find manifest from design name')
        else:
            chip.read_manifest(manifest)

    # Read in file
    if filename:
        chip.logger.info(f"Displaying {filename}")

    # Set supported showtools incase custom flow was used and didn't get set
    set_common_showtools(chip)

    success = chip.show(filename)

    return 0 if success else 1


#########################
if __name__ == "__main__":
    sys.exit(main())
