# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import os
import siliconcompiler

def main():
    progname = "sc-show"
    description = """
    --------------------------------------------------------------
    Restricted SC app that displays the layout of a design
    based on a file provided or tries to display the final
    layout based on loading the json manifest from:
    build/<design>/job0/import/0/outputs/<design>.pkg.json

    Examples:

    sc-show -design adder
    (displays build/adder/export/0/outputs/adder.gds)

    sc-show build/adder/route/1/outputs/adder.def
    (displays build/adder/route/1/outputs/adder.def)

    """

    chip = siliconcompiler.Chip()
    chip.create_cmdline(progname,
                        switchlist=['design', 'asic_gds', 'asic_def', 'loglevel', 'cfg'],
                        description=description)

    #Error checking
    gds_mode =bool(chip.get('asic', 'gds'))
    def_mode =bool(chip.get('asic', 'def'))

    if (def_mode + gds_mode) > 1:
        print(progname+": error: gds, def options are mutually exclusive")
        sys.exit()

    if gds_mode:
        filename = chip.get('asic', 'gds')[-1]
    elif def_mode:
        filename = chip.get('asic', 'def')[-1]
    else:
        design = chip.get('design')
        dirlist =[chip.cwd,
                  'build',
                  chip.get('design'),
                  'job0',
                  'import',
                  '0',
                  'outputs',
                  design + '.pkg.json']
        manifest = os.path.join(*dirlist)
        chip.read_manifest(manifest)
        filename = None

    if chip.get('cfg') is None:
        # only autoload manifest if user doesn't supply manually
        design = os.path.splitext(os.path.basename(filename))[0]
        dirname = os.path.dirname(filename)
        manifest = os.path.join(*[dirname, design+'.pkg.json'])
        chip.read_manifest(manifest)

    # Read in file
    chip.logger.info("Displaying filename")
    chip.show(filename)

#########################
if __name__ == "__main__":
    sys.exit(main())
