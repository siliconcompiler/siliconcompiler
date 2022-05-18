import os
import siliconcompiler

def make_docs():
    '''
    ASAP 7 7.5-track standard cell library.
    '''
    chip =  siliconcompiler.Chip('<design>')
    setup(chip)
    return chip

def _setup_lib(libname, suffix):
    lib = siliconcompiler.Chip(libname)

    group = 'asap7sc7p5t'
    vt = 'rvt'
    libname = f'{group}_{vt}'
    foundry = 'virtual'
    process = 'asap7'
    stackup = '10M'
    libtype = '7p5t'
    rev = 'r1p7'
    corner = 'typical'
    objectives = ['setup']

    libdir = os.path.join('..', 'third_party', 'pdks', foundry, process, 'libs', libname, rev)

    # rev
    lib.set('package', 'version',rev)

    lib.set('asic', 'pdk', 'asap7')

    # timing
    lib.add('model', 'timing', 'nldm', corner,
            libdir+'/nldm/'+libname+'_ff.lib')

    # lef
    lib.add('model', 'layout', 'lef', stackup,
                libdir+'/lef/'+libname+'.lef')
    # gds
    lib.add('model', 'layout', 'gds', stackup,
                libdir+'/gds/'+libname+'.gds')

    # site name
    lib.set('asic', 'footprint', 'asap7sc7p5t', 'symmetry', 'Y')
    lib.set('asic', 'footprint', 'asap7sc7p5t', 'size', (0.054,0.270))

    # lib arch
    lib.set('asic', 'libarch', libtype)

    #default input driver
    lib.add('asic', 'cells', 'driver', f"BUFx2_ASAP7_75t_{suffix}")

    # clock buffers
    lib.add('asic', 'cells', 'clkbuf', f"BUFx2_ASAP7_75t_{suffix}")

    # tie cells
    lib.add('asic', 'cells', 'tie', [f"TIEHIx1_ASAP7_75t_{suffix}/H",
                                        f"TIELOx1_ASAP7_75t_{suffix}/L"])

    # buffer
    # TODO: Need to fix this syntax!, not needed by modern tools!
    lib.add('asic', 'cells', 'buf', [f"BUFx2_ASAP7_75t_{suffix}/A/Y"])

    # hold cells
    lib.add('asic', 'cells', 'hold', f"BUFx2_ASAP7_75t_{suffix}")

    # filler
    lib.add('asic', 'cells', 'filler', [f"FILLER_ASAP7_75t_{suffix}"])

    # Stupid small cells
    lib.add('asic', 'cells', 'ignore', ["*x1_ASAP7*",
                                        "*x1p*_ASAP7*",
                                        "*xp*_ASAP7*",
                                        "SDF*",
                                        "ICG*",
                                        "DFFH*"])

    # Tapcell
    lib.add('asic', 'cells', 'tap', f"TAPCELL_ASAP7_75t_{suffix}")

    # Endcap
    lib.add('asic', 'cells','endcap', f"DECAPx1_ASAP7_75t_{suffix}")

    # Techmap
    if libname.endswith('rvt'):
        # TODO: write map files for other groups
        lib.add('asic', 'file', 'yosys', 'techmap',
                    libdir + '/techmap/yosys/cells_latch.v')

    return lib

def setup(chip):
    all_libs = {
        'asap7sc7p5t_rvt' : 'R',
        'asap7sc7p5t_lvt' : 'L',
        'asap7sc7p5t_slvt' : 'SL'
    }

    for libname, suffix in all_libs.items():
        lib = _setup_lib(libname, suffix)
        chip.import_library(lib)
