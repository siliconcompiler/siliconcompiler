import os
import siliconcompiler


def setup(stackup=None):
    # Core values.
    design = 'sky130_sram_2k'

    if stackup is None:
        raise RuntimeError('stackup cannot be None')

    # Create library Chip object.
    lib = siliconcompiler.Library(design)
    lib.register_source('vlsida',
                        'git+https://github.com/VLSIDA/sky130_sram_macros',
                        'c2333394e0b0b9d9d71185678a8d8087715d5e3b')
    lib.set('output', stackup, 'gds',
            'sky130_sram_2kbyte_1rw1r_32x512_8/sky130_sram_2kbyte_1rw1r_32x512_8.gds',
            package='vlsida')
    lib.set('output', stackup, 'lef',
            'sky130_sram_2kbyte_1rw1r_32x512_8/sky130_sram_2kbyte_1rw1r_32x512_8.lef',
            package='vlsida')

    rootdir = os.path.dirname(__file__)
    lib.set('output', 'blackbox', 'verilog', os.path.join(rootdir, "sky130_sram_2k.bb.v"))
    # Ensure this file gets uploaded to remote
    lib.set('output', 'blackbox', 'verilog', True, field='copy')

    return lib
