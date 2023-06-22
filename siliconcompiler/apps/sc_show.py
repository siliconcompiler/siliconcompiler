# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import os
import glob
import siliconcompiler
from siliconcompiler.utils import get_default_iomap
from siliconcompiler.targets.utils import set_common_showtools


def _get_manifest(dirname):
    # pkg.json file may have a different name from the design due to the entrypoint
    glob_paths = [os.path.join(dirname, '*.pkg.json'),
                  os.path.join(dirname, 'outputs', '*.pkg.json')]
    manifest = None
    for path in glob_paths:
        manifest = glob.glob(path)
        if manifest:
            manifest = manifest[0]
            break

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
    (displays build/adder/job0/export/0/outputs/adder.gds)

    sc-show -design adder -arg_step floorplan
    (displays build/adder/job0/floorplan/0/outputs/adder.def)

    sc-show -design adder -arg_step place -arg_index 1
    (displays build/adder/job0/place/1/outputs/adder.def)

    sc-show -design adder -jobname rtl2gds
    (displays build/adder/rtl2gds/export/0/outputs/adder.gds)

    sc-show -cfg build/adder/rtl2gds/adder.pkg.json
    (displays build/adder/rtl2gds/export/0/outputs/adder.gds)

    sc-show -design adder -ext odb
    (displays build/adder/job0/export/1/outputs/adder.odb)

    sc-show build/adder/job0/route/1/outputs/adder.def
    (displays build/adder/job0/route/1/outputs/adder.def)
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

    extension_arg = {
        'metavar': '<ext>',
        'help': '(optional) Specify the extension of the file to show.'
    }
    screenshot_arg = {
        'action': 'store_true',
        'help': '(optional) Will generate a screenshot and exit.'
    }

    args = chip.create_cmdline(
        progname,
        switchlist=['-design',
                    '-input',
                    '-loglevel',
                    '-cfg',
                    '-arg_step',
                    '-arg_index',
                    '-jobname'],
        description=description,
        input_map=input_map,
        additional_args={
            '-ext': extension_arg,
            '-screenshot': screenshot_arg
        })

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
        chip.logger.error('Nothing to load: please define a target with '
                          '-cfg, -design, and/or inputs.')
        return 1

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
            return 1
        chip.read_manifest(manifest)
    elif not chip.get('option', 'cfg'):
        manifest = _get_manifest(chip._getworkdir(jobname=chip.get('option', 'jobname'),
                                                  step=chip.get('arg', 'step'),
                                                  index=chip.get('arg', 'index')))
        if not manifest:
            chip.logger.error('Could not find manifest from design name')
            return 1
        else:
            chip.read_manifest(manifest)

    # Read in file
    if filename:
        chip.logger.info(f"Displaying {filename}")

    # Set supported showtools incase custom flow was used and didn't get set
    set_common_showtools(chip)

    success = chip.show(filename,
                        extension=args['ext'],
                        screenshot=args['screenshot'])

    if args['screenshot'] and os.path.isfile(success):
        chip.logger.info(f'Screenshot file: {success}')

    return 0 if success else 1


#########################
if __name__ == "__main__":
    sys.exit(main())
