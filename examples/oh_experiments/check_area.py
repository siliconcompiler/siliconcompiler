#!/usr/bin/env python3

import siliconcompiler
from siliconcompiler import package as sc_package

import glob
import os
import re
import sys


def __register_oh(chip):
    chip.register_source('oh',
                         'git+https://github.com/aolofsson/oh',
                         '23b26c4a938d4885a2a340967ae9f63c3c7a3527')


def checkarea(filelist, libdir, target):
    '''
    Runs SC through synthesis and prints out the module name, cell count,
    and area as a csv format ready to be imported into a spreadsheet
    program.

    Args:
    filelist (list): List of files to process. Naming should be "module".v.
    libdir (str): Path to required Verilog sources.
    target (str): Name of the SC target. For example, freepdk45_demo.
    '''

    print("module", "cells", "area", sep=",")
    for item in filelist:
        design = re.match(r'.*/(\w+)\.v', item).group(1)
        chip = siliconcompiler.Chip(design)
        __register_oh(chip)
        chip.use(target)
        chip.input(item)
        chip.add('option', 'ydir', libdir, package='oh')
        chip.set('option', 'quiet', True)
        chip.set('option', 'to', ['syn'])
        chip.run()
        cells = chip.get('metric', 'cells', step='syn', index='0')
        area = chip.get('metric', 'cellarea', step='syn', index='0')
        print(design, cells, area, sep=",")

    return 0


def main(limit=-1):
    # Checking asiclib
    libdir = os.path.join('asiclib', 'hdl')

    chip = siliconcompiler.Chip('oh')
    __register_oh(chip)
    filelist = glob.glob(sc_package.path(chip, 'oh') + '/' + libdir + '/*.v')
    dontcheck = ['asic_keeper.v',
                 'asic_antenna.v',
                 'asic_header.v',
                 'asic_footer.v',
                 'asic_decap.v']
    for item in dontcheck:
        filelist.remove(os.path.join(sc_package.path(chip, 'oh') + '/' + libdir, item))

    filelist = sorted(filelist)[0:limit]
    return checkarea(filelist, libdir, 'freepdk45_demo')


#########################
if __name__ == "__main__":
    sys.exit(main())
