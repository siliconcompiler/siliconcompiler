import os
import siliconcompiler

def make_docs():
    chip =  siliconcompiler.Chip('<design>')
    return setup(chip)

def _setup_lib(chip, libname, suffix):
    lib = siliconcompiler.Library(chip, libname)

    group = 'asap7sc7p5t'
    vt = 'rvt'
    libname = f'{group}_{vt}'
    foundry = 'virtual'
    process = 'asap7'
    stackup = '10M'
    libtype = '7p5t'
    rev = 'r1p7'
    corners = {'typical': 'tt',
               'fast': 'ff',
               'slow': 'ss'}

    libdir = os.path.join('..', 'third_party', 'pdks', foundry, process, 'libs', libname, rev)

    # rev
    lib.set('package', 'version',rev)

    # todo: remove later
    lib.set('option', 'pdk', 'asap7')

    # timing
    for corner_name, lib_corner in corners.items():
        lib.add('output', corner_name, 'nldm', libdir+'/nldm/'+libname+'_' + lib_corner + '.lib.gz')

    # lef
    lib.add('output', stackup, 'lef', libdir+'/lef/'+libname+'.lef')

    # gds
    lib.add('output', stackup, 'gds', libdir+'/gds/'+libname+'.gds')

    # cdl
    lib.add('output', stackup, 'cdl', libdir+'/netlist/'+libname+'.cdl')

    # lib arch
    lib.set('asic', 'libarch', libtype)

    # site name
    lib.set('asic', 'site', libtype, 'asap7sc7p5t')

    # clock buffers
    lib.add('asic', 'cells', 'clkbuf', f"BUFx2_ASAP7_75t_{suffix}")

    # tie cells
    lib.add('asic', 'cells', 'tie', [f"TIEHIx1_ASAP7_75t_{suffix}",
                                     f"TIELOx1_ASAP7_75t_{suffix}"])

    # hold cells
    lib.add('asic', 'cells', 'hold', f"BUFx2_ASAP7_75t_{suffix}")

    # filler
    lib.add('asic', 'cells', 'filler', [f"FILLER_ASAP7_75t_{suffix}"])

    # Stupid small cells
    lib.add('asic', 'cells', 'dontuse', ["*x1_ASAP7*",
                                         "*x1p*_ASAP7*",
                                         "*xp*_ASAP7*",
                                         "SDF*",
                                         "ICG*",
                                         "DFFH*"])

    # Tapcell
    lib.add('asic', 'cells', 'tap', f"TAPCELL_ASAP7_75t_{suffix}")

    # Endcap
    lib.add('asic', 'cells','endcap', f"DECAPx1_ASAP7_75t_{suffix}")

    # Yosys techmap
    if libname.endswith('rvt'):
        # TODO: write map files for other groups
        lib.add('option', 'file', 'yosys_techmap', libdir + '/techmap/yosys/cells_latch.v')

    # Defaults for OpenROAD tool variables
    lib.set('option', 'var', 'openroad_place_density', '0.77')
    lib.set('option', 'var', 'openroad_pad_global_place', '2')
    lib.set('option', 'var', 'openroad_pad_detail_place', '1')
    lib.set('option', 'var', 'openroad_macro_place_halo', ['22.4', '15.12'])
    lib.set('option', 'var', 'openroad_macro_place_channel', ['18.8', '19.95'])

    lib.set('option', 'var', 'yosys_driver_cell', f"BUFx2_ASAP7_75t_{suffix}")
    lib.set('option', 'var', 'yosys_buffer_cell', f"BUFx2_ASAP7_75t_{suffix}")
    lib.set('option', 'var', 'yosys_buffer_input', "A")
    lib.set('option', 'var', 'yosys_buffer_output', "Y")
    for tool in ('yosys', 'openroad'):
        lib.set('option', 'var', f'{tool}_tiehigh_cell', f"TIEHIx1_ASAP7_75t_{suffix}")
        lib.set('option', 'var', f'{tool}_tiehigh_port', "H")
        lib.set('option', 'var', f'{tool}_tielow_cell', f"TIELOx1_ASAP7_75t_{suffix}")
        lib.set('option', 'var', f'{tool}_tielow_port', "L")

    # Openroad APR setup files
    lib.set('option', 'file', 'openroad_tracks', libdir + '/apr/openroad/tracks.tcl')
    lib.set('option', 'file', 'openroad_tapcells', libdir + '/apr/openroad/tapcells.tcl')
    lib.set('option', 'file', 'openroad_pdngen', libdir + '/apr/openroad/pdngen.tcl')
    lib.set('option', 'file', 'openroad_global_connect', libdir + '/apr/openroad/global_connect.tcl')

    return lib

def setup(chip):
    '''
    ASAP 7 7.5-track standard cell library.
    '''
    all_libs = {
        'asap7sc7p5t_rvt' : 'R',
        'asap7sc7p5t_lvt' : 'L',
        'asap7sc7p5t_slvt' : 'SL'
    }

    libs = []
    for libname, suffix in all_libs.items():
        libs.append(_setup_lib(chip, libname, suffix))

    return libs
