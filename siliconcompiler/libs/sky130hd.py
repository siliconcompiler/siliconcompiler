import os
import siliconcompiler


def setup(chip):
    '''
    Skywater130 standard cell library.
    '''
    foundry = 'skywater'
    process = 'skywater130'
    stackup = '5M1LI'
    version = 'v0_0_2'
    libname = 'sky130hd'  # not sure if this should be something else
    libtype = 'unithd'  # TODO: update this

    libdir = os.path.join('..', 'third_party', 'pdks', foundry, process, 'libs', libname, version)

    lib = siliconcompiler.Library(chip, libname)

    # version
    lib.set('package', 'version', version)

    # pdk
    lib.set('option', 'pdk', 'skywater130')

    # footprint/type/sites
    lib.set('asic', 'libarch', libtype)
    lib.set('asic', 'site', libtype, 'unithd')
    lib.add('asic', 'site', libtype, 'unithddbl')

    # model files
    lib.add('output', 'slow', 'nldm', libdir + '/lib/sky130_fd_sc_hd__ss_n40C_1v40.lib.gz')
    lib.add('output', 'typical', 'nldm', libdir + '/lib/sky130_fd_sc_hd__tt_025C_1v80.lib.gz')
    lib.add('output', 'fast', 'nldm', libdir + '/lib/sky130_fd_sc_hd__ff_100C_1v95.lib.gz')

    lib.add('output', stackup, 'lef', libdir + '/lef/sky130_fd_sc_hd_merged.lef')
    lib.add('output', stackup, 'gds', libdir + '/gds/sky130_fd_sc_hd.gds')
    lib.add('output', stackup, 'cdl', libdir + '/cdl/sky130_fd_sc_hd.cdl')

    # antenna cells
    lib.add('asic', 'cells', 'antenna', 'sky130_fd_sc_hd__diode_2')

    # clock buffers
    lib.add('asic', 'cells', 'clkbuf', ['sky130_fd_sc_hd__clkbuf_1',
                                        'sky130_fd_sc_hd__clkbuf_2',
                                        'sky130_fd_sc_hd__clkbuf_4',
                                        'sky130_fd_sc_hd__clkbuf_6',
                                        'sky130_fd_sc_hd__clkbuf_8',
                                        'sky130_fd_sc_hd__clkbuf_12',
                                        'sky130_fd_sc_hd__clkbuf_16'])

    # hold cells
    lib.add('asic', 'cells', 'hold', ['sky130_fd_sc_hd__buf_1',
                                      'sky130_fd_sc_hd__buf_2',
                                      'sky130_fd_sc_hd__buf_4',
                                      'sky130_fd_sc_hd__buf_6',
                                      'sky130_fd_sc_hd__buf_8',
                                      'sky130_fd_sc_hd__buf_12',
                                      'sky130_fd_sc_hd__buf_16'])

    # filler
    lib.add('asic', 'cells', 'filler', ['sky130_fd_sc_hd__fill_1',
                                        'sky130_fd_sc_hd__fill_2',
                                        'sky130_fd_sc_hd__fill_4',
                                        'sky130_fd_sc_hd__fill_8'])

    # Tapcell
    lib.add('asic', 'cells', 'tap', 'sky130_fd_sc_hd__tapvpwrvgnd_1')

    # Endcap
    lib.add('asic', 'cells', 'endcap', 'sky130_fd_sc_hd__decap_4')

    lib.add('asic', 'cells', 'dontuse', [
        'sky130_fd_sc_hd__probe_p_8',
        'sky130_fd_sc_hd__probec_p_8',
        'sky130_fd_sc_hd__lpflow_bleeder_1',
        'sky130_fd_sc_hd__lpflow_clkbufkapwr_1',
        'sky130_fd_sc_hd__lpflow_clkbufkapwr_16',
        'sky130_fd_sc_hd__lpflow_clkbufkapwr_2',
        'sky130_fd_sc_hd__lpflow_clkbufkapwr_4',
        'sky130_fd_sc_hd__lpflow_clkbufkapwr_8',
        'sky130_fd_sc_hd__lpflow_clkinvkapwr_1',
        'sky130_fd_sc_hd__lpflow_clkinvkapwr_16',
        'sky130_fd_sc_hd__lpflow_clkinvkapwr_2',
        'sky130_fd_sc_hd__lpflow_clkinvkapwr_4',
        'sky130_fd_sc_hd__lpflow_clkinvkapwr_8',
        'sky130_fd_sc_hd__lpflow_decapkapwr_12',
        'sky130_fd_sc_hd__lpflow_decapkapwr_3',
        'sky130_fd_sc_hd__lpflow_decapkapwr_4',
        'sky130_fd_sc_hd__lpflow_decapkapwr_6',
        'sky130_fd_sc_hd__lpflow_decapkapwr_8',
        'sky130_fd_sc_hd__lpflow_inputiso0n_1',
        'sky130_fd_sc_hd__lpflow_inputiso0p_1',
        'sky130_fd_sc_hd__lpflow_inputiso1n_1',
        'sky130_fd_sc_hd__lpflow_inputiso1p_1',
        'sky130_fd_sc_hd__lpflow_inputisolatch_1',
        'sky130_fd_sc_hd__lpflow_isobufsrc_1',
        'sky130_fd_sc_hd__lpflow_isobufsrc_16',
        'sky130_fd_sc_hd__lpflow_isobufsrc_2',
        'sky130_fd_sc_hd__lpflow_isobufsrc_4',
        'sky130_fd_sc_hd__lpflow_isobufsrc_8',
        'sky130_fd_sc_hd__lpflow_isobufsrckapwr_16',
        'sky130_fd_sc_hd__lpflow_lsbuf_lh_hl_isowell_tap_1',
        'sky130_fd_sc_hd__lpflow_lsbuf_lh_hl_isowell_tap_2',
        'sky130_fd_sc_hd__lpflow_lsbuf_lh_hl_isowell_tap_4',
        'sky130_fd_sc_hd__lpflow_lsbuf_lh_isowell_4',
        'sky130_fd_sc_hd__lpflow_lsbuf_lh_isowell_tap_1',
        'sky130_fd_sc_hd__lpflow_lsbuf_lh_isowell_tap_2',
        'sky130_fd_sc_hd__lpflow_lsbuf_lh_isowell_tap_4'
    ])

    # tie cells
    lib.add('asic', 'cells', 'tie', ['sky130_fd_sc_hd__conb_1'])

    # Defaults for OpenROAD tool variables
    lib.set('option', 'var', 'openroad_place_density', '0.6')
    lib.set('option', 'var', 'openroad_pad_global_place', '1')
    lib.set('option', 'var', 'openroad_pad_detail_place', '0')
    lib.set('option', 'var', 'openroad_macro_place_halo', ['40', '40'])
    lib.set('option', 'var', 'openroad_macro_place_channel', ['80', '80'])

    # Yosys techmap
    lib.add('option', 'file', 'yosys_techmap', libdir + '/techmap/yosys/cells_latch.v')
    lib.add('option', 'file', 'yosys_addermap', libdir + '/techmap/yosys/cells_adders.v')

    # Openroad specific files
    lib.set('option', 'file', 'openroad_pdngen',
            libdir + '/apr/openroad/pdngen.tcl')
    lib.set('option', 'file', 'openroad_global_connect',
            libdir + '/apr/openroad/global_connect.tcl')
    lib.set('option', 'file', 'openroad_tapcells',
            libdir + '/apr/openroad/tapcell.tcl')

    lib.set('option', 'var', 'openroad_cts_clock_buffer', "sky130_fd_sc_hd__clkbuf_4")

    lib.set('option', 'var', 'yosys_abc_clock_multiplier', "1000")  # convert from ns -> ps
    lib.set('option', 'var', 'yosys_driver_cell', "sky130_fd_sc_hd__buf_4")
    lib.set('option', 'var', 'yosys_buffer_cell', "sky130_fd_sc_hd__buf_4")
    lib.set('option', 'var', 'yosys_buffer_input', "A")
    lib.set('option', 'var', 'yosys_buffer_output', "X")
    for tool in ('yosys', 'openroad'):
        lib.set('option', 'var', f'{tool}_tiehigh_cell', "sky130_fd_sc_hd__conb_1")
        lib.set('option', 'var', f'{tool}_tiehigh_port', "HI")
        lib.set('option', 'var', f'{tool}_tielow_cell', "sky130_fd_sc_hd__conb_1")
        lib.set('option', 'var', f'{tool}_tielow_port', "LO")

    return lib


#########################
if __name__ == "__main__":
    lib = setup(siliconcompiler.Chip('<lib>'))
    lib.write_manifest(f'{lib.top()}.json')
