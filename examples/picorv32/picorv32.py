#!/usr/bin/env python3

import os
import siliconcompiler


def rtl2gds(design='picorv32',
            target="skywater130_demo",
            sdc=None,
            rtl=None,
            width=1000,
            height=1000,
            jobname='job0',
            fp=None):
    '''RTL2GDS flow'''

    # CREATE OBJECT
    chip = siliconcompiler.Chip(design)

    # SETUP
    chip.register_package_source(name='picorv32',
                                 path='git+https://github.com/YosysHQ/picorv32.git',
                                 ref='c0acaebf0d50afc6e4d15ea9973b60f5f4d03c42')

    chip.load_target(target)
    rootdir = os.path.dirname(__file__)
    if rtl is None:
        chip.input('picorv32.v', package='picorv32')
    if sdc is None:
        chip.input(os.path.join(rootdir, f"{design}.sdc"))

    chip.set('option', 'relax', True)
    chip.set('option', 'quiet', True)

    chip.set('constraint', 'outline', [(0, 0), (width, height)])
    chip.set('constraint', 'corearea', [(10, 10), (width - 10, height - 10)])

    # RUN
    chip.run()

    # ANALYZE
    chip.summary()

    return chip


if __name__ == '__main__':
    rtl2gds()
