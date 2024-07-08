#!/usr/bin/env python3

import os
import siliconcompiler


def rtl2gds(design='aes',
            target="freepdk45_demo",
            sdc=None,
            rtl=None,
            width=200,
            height=200,
            jobname='job0',
            fp=None):
    '''RTL2GDS flow'''

    # CREATE OBJECT
    chip = siliconcompiler.Chip(design)

    # TARGET
    chip.load_target(target)

    # FLOW OVERLOAD
    rootdir = os.path.dirname(__file__)
    if rtl is None:
        chip.input(os.path.join(rootdir, f"{design}.v"))
    if sdc is None:
        chip.input(os.path.join(rootdir, f"{design}.sdc"))

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
