#!/usr/bin/env python3
import siliconcompiler


def rtl2gds(target="skywater130_demo"):
    '''RTL2GDS flow'''

    # CREATE OBJECT
    chip = siliconcompiler.Chip('picorv32')

    # SETUP
    chip.use(target)

    chip.register_source(name='picorv32',
                         path='git+https://github.com/YosysHQ/picorv32.git',
                         ref='c0acaebf0d50afc6e4d15ea9973b60f5f4d03c42')

    chip.input('picorv32.v', package='picorv32')

    chip.set('option', 'quiet', True)
    chip.set('option', 'remote', False)

    chip.clock('clk', period=25)

    # RUN
    chip.run()

    # ANALYZE
    chip.summary()

    return chip


if __name__ == '__main__':
    rtl2gds()
