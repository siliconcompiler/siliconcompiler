# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import os
import siliconcompiler
from siliconcompiler.utils import get_default_iomap
from siliconcompiler.apps._common import load_manifest, manifest_switches
from siliconcompiler.utils import get_file_ext


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
    (displays build/adder/job0/write_gds/0/outputs/adder.gds)

    sc-show -design adder -arg_step floorplan
    (displays build/adder/job0/floorplan/0/outputs/adder.def)

    sc-show -design adder -arg_step place -arg_index 1
    (displays build/adder/job0/place/1/outputs/adder.def)

    sc-show -design adder -jobname rtl2gds
    (displays build/adder/rtl2gds/write_gds/0/outputs/adder.gds)

    sc-show -cfg build/adder/rtl2gds/adder.pkg.json
    (displays build/adder/rtl2gds/write_gds/0/outputs/adder.gds)

    sc-show -design adder -ext odb
    (displays build/adder/job0/write_data/0/outputs/adder.odb)

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
    for ext in chip._showtools:
        if ext in default_input_map:
            input_map[ext] = default_input_map[ext]

    extension_arg = {
        'metavar': '<ext>',
        'help': '(optional) Specify the extension of the file to show.',
        'sc_print': False
    }
    screenshot_arg = {
        'action': 'store_true',
        'help': '(optional) Will generate a screenshot and exit.',
        'sc_print': False
    }

    try:
        args = chip.create_cmdline(
            progname,
            switchlist=[*manifest_switches(),
                        '-input',
                        '-loglevel'],
            description=description,
            input_map=input_map,
            additional_args={
                '-ext': extension_arg,
                '-screenshot': screenshot_arg
            })
    except Exception as e:
        chip.logger.error(e)
        return 1

    # Error checking
    design = chip.get('design')
    design_set = design != UNSET_DESIGN

    # Search input keys for files
    input_mode = []
    for fileset in chip.getkeys('input'):
        for mode in chip.getkeys('input', fileset):
            if chip.schema._getvals('input', fileset, mode):
                input_mode = [('input', fileset, mode)]

    if not (design_set or input_mode):
        chip.logger.error('Nothing to load: please define a target with '
                          '-cfg, -design, and/or inputs.')
        return 1

    filename = None
    if input_mode:
        check_ext = list(chip._showtools.keys())

        if args['ext']:
            check_ext = [args['ext']]

        def get_file_from_keys():
            for ext in check_ext:
                for key in input_mode:
                    for files, _, _ in chip.schema._getvals(*key):
                        for file in files:
                            if get_file_ext(file) == ext:
                                return file
            return None

        filename = get_file_from_keys()

    if not load_manifest(chip, filename):
        return 1

    # Read in file
    if filename:
        chip.logger.info(f"Displaying {filename}")

    if not chip.find_files('option', 'builddir', missing_ok=True):
        chip.logger.warning("Unable to access original build directory "
                            f"\"{chip.get('option', 'builddir')}\", using \"build\" instead")
        chip.set('option', 'builddir', 'build')

    success = chip.show(filename,
                        extension=args['ext'],
                        screenshot=args['screenshot'])

    if args['screenshot'] and os.path.isfile(success):
        chip.logger.info(f'Screenshot file: {success}')

    return 0 if success else 1


#########################
if __name__ == "__main__":
    sys.exit(main())
