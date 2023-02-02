import os
import siliconcompiler

def setup(chip):
    # Core values.
    design = 'sky130_sram_2k'
    stackup = chip.get('option', 'stackup')

    # Create library Chip object.
    lib = siliconcompiler.Chip(design)
    libdir = os.path.dirname(__file__)
    lib.set('output', stackup, 'gds', f'{libdir}/sky130_sram_2kbyte_1rw1r_32x512_8.gds.gz')
    lib.set('output', stackup, 'lef', f'{libdir}/sky130_sram_2kbyte_1rw1r_32x512_8.lef')

    # TODO: We'll probably want to 'return lib' instead, once 'chip.use' is finalized.
    chip._loaded_modules['libs'].append(design)
    chip.import_library(lib)
