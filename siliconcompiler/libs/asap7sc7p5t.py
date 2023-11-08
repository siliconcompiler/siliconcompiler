import os
import siliconcompiler


def _setup_lib(chip, libname, suffix):
    lib = siliconcompiler.Library(chip, libname)

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
    lib.set('package', 'version', rev)

    # todo: remove later
    lib.set('option', 'pdk', 'asap7')

    # timing
    for corner_name, lib_corner in corners.items():
        lib.add('output', corner_name, 'nldm',
                libdir + '/nldm/' + libname + '_' + lib_corner + '.lib.gz')

    # lef
    lib.add('output', stackup, 'lef', libdir + '/lef/' + libname + '.lef')

    # gds
    lib.add('output', stackup, 'gds', libdir + '/gds/' + libname + '.gds')

    # cdl
    lib.add('output', stackup, 'cdl', libdir + '/netlist/' + libname + '.cdl')

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
    lib.add('asic', 'cells', 'filler', [f"FILLER_ASAP7_75t_{suffix}",
                                        f"FILLERxp5_ASAP7_75t_{suffix}"])

    # decap
    lib.add('asic', 'cells', 'decap', [f"DECAPx1_ASAP7_75t_{suffix}",
                                       f"DECAPx1_ASAP7_75t_{suffix}",
                                       f"DECAPx3_ASAP7_75t_{suffix}",
                                       f"DECAPx6_ASAP7_75t_{suffix}",
                                       f"DECAPx10_ASAP7_75t_{suffix}"])

    # Stupid small cells
    lib.add('asic', 'cells', 'dontuse', ["[!ASYNC]*x1_ASAP7*",
                                         "*x1p*_ASAP7*",
                                         "*xp*_ASAP7*",
                                         "SDF*",
                                         "ICG*",
                                         "DFFH*"])

    # Tapcell
    lib.add('asic', 'cells', 'tap', f"TAPCELL_ASAP7_75t_{suffix}")

    # Endcap
    lib.add('asic', 'cells', 'endcap', f"DECAPx1_ASAP7_75t_{suffix}")

    # Yosys techmap
    lib.add('option', 'file', 'yosys_techmap', libdir + '/techmap/yosys/cells_latch.v')
    lib.add('option', 'file', 'yosys_addermap', libdir + '/techmap/yosys/cells_adders.v')
    lib.set('option', 'file', 'yosys_dff_liberty',
            libdir + '/nldm/' + libname + '_' + 'ss.lib.gz')

    # Defaults for OpenROAD tool variables
    lib.set('option', 'var', 'openroad_place_density', '0.60')
    lib.set('option', 'var', 'openroad_pad_global_place', '2')
    lib.set('option', 'var', 'openroad_pad_detail_place', '1')
    lib.set('option', 'var', 'openroad_macro_place_halo', ['10', '10'])
    lib.set('option', 'var', 'openroad_macro_place_channel', ['12', '12'])

    lib.set('option', 'var', 'openroad_cts_clock_buffer', f"BUFx4_ASAP7_75t_{suffix}")
    lib.set('option', 'var', 'openroad_cts_distance_between_buffers', "60")

    lib.set('option', 'var', 'yosys_abc_clock_multiplier', "1")  # convert from ps -> ps
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
    lib.set('option', 'file', 'openroad_tracks',
            libdir + '/apr/openroad/tracks.tcl')
    lib.set('option', 'file', 'openroad_tapcells',
            libdir + '/apr/openroad/tapcells.tcl')
    lib.set('option', 'file', 'openroad_pdngen',
            libdir + '/apr/openroad/pdngen.tcl')
    lib.set('option', 'file', 'openroad_global_connect',
            libdir + '/apr/openroad/global_connect.tcl')

    return lib


def setup(chip):
    '''
    ASAP 7 7.5-track standard cell library.
    '''
    all_libs = {
        'asap7sc7p5t_rvt': 'R',
        'asap7sc7p5t_lvt': 'L',
        'asap7sc7p5t_slvt': 'SL'
    }

    libs = []
    for libname, suffix in all_libs.items():
        libs.append(_setup_lib(chip, libname, suffix))

    return libs


#########################
if __name__ == "__main__":
    for lib in setup(siliconcompiler.Chip('<lib>')):
        lib.write_manifest(f'{lib.top()}.json')
