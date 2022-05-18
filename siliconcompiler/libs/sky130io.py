import os

import siliconcompiler

def make_docs():
    '''
    Skywater130 I/O library.
    '''
    chip = siliconcompiler.Chip('<design>')
    setup(chip)
    return chip

def setup(chip):
    process = 'skywater130'
    libname = 'sky130io'
    stackup = '5M1LI'

    lib = siliconcompiler.Chip(libname)

    libdir = os.path.join('..',
                          'third_party',
                          'pdks',
                          'skywater',
                          process,
                          'libs',
                          libname,
                          'v0_0_2',
                          'io')

    lib.set('asic', 'pdk', 'skywater130')
    lib.set('asic', 'stackup', stackup)

    lib.set('model', 'timing', 'nldm', 'typical', os.path.join(libdir, 'sky130_dummy_io.lib'))
    lib.set('model', 'layout', 'lef', stackup, os.path.join(libdir, 'sky130_ef_io.lef'))

    # Need both GDS files: ef relies on fd one
    lib.add('model', 'layout', 'gds', stackup, os.path.join(libdir, 'sky130_ef_io.gds'))
    lib.add('model', 'layout', 'gds', stackup, os.path.join(libdir, 'sky130_fd_io.gds'))
    lib.add('model', 'layout', 'gds', stackup, os.path.join(libdir, 'sky130_ef_io__gpiov2_pad_wrapped.gds'))

    chip.import_library(lib)
