#!/usr/bin/env python3

import os
import siliconcompiler

def rtl2gds(design='aes',
            target="skywater130_demo",
            sdc=None,
            rtl=None,
            width=1500,
            height=1500,
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
        chip.add('input', 'verilog', os.path.join(rootdir, f"{design}.v"))
    if sdc is None:
        chip.add('input', 'sdc', os.path.join(rootdir, f"{design}.sdc"))

    chip.set('option', 'relax', True)
    chip.set('option', 'quiet', True)

    chip.set('asic', 'diearea', [(0,0), (width,height)])
    chip.set('asic', 'corearea', [(10,10), (width-10,height-10)])

    # RUN
    chip.run()

    # ANALYZE
    chip.summary()

    return chip

if __name__ == '__main__':
    rtl2gds()
