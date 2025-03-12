#!/usr/bin/env python3

from siliconcompiler import Chip
from siliconcompiler.targets import freepdk45_demo


def rtl2gds(target=freepdk45_demo,
            sdc=None,
            rtl=None,
            width=200,
            height=200):
    '''RTL2GDS flow'''

    # CREATE OBJECT
    chip = Chip("aes")

    # TARGET
    chip.use(target)

    # FLOW OVERLOAD
    chip.register_source("aes-example", __file__)
    if rtl is None:
        chip.input("aes.v", package="aes-example")
    if sdc is None:
        chip.input("aes.sdc", package="aes-example")

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
