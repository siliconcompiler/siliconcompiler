import os
import siliconcompiler

def make_docs():
    '''
    Skywater130 standard cell library.
    '''

    chip = siliconcompiler.Chip()
    setup(chip)
    return chip

def setup(chip):

    foundry = 'skywater'
    process = 'skywater130'
    rev = 'v0_0_2'
    libname = 'sky130hd' # not sure if this should be something else
    libtype = 'hd' # TODO: update this

    # TODO: should I be using a different name for the corner
    corner = 'typical'

    libdir = os.path.join('..', 'third_party', 'pdks', foundry, process, 'libs', libname, rev)


    chip.set('library', libname, 'type', 'stdcell')

    # rev
    chip.set('library', libname, 'package', 'version', rev)

    chip.set('library', libname, 'pdk', 'skywater130')

    # timing
    chip.add('library', libname, 'nldm', corner, 'lib',
             libdir+'/lib/sky130_fd_sc_hd__tt_025C_1v80.lib')

    # lef
    chip.add('library', libname, 'lef',
             libdir+'/lef/sky130_fd_sc_hd_merged.lef')
    # gds
    chip.add('library', libname, 'gds',
             libdir+'/gds/sky130_fd_sc_hd.gds')

    # placement sites
    chip.set('library', libname, 'site', 'unithd', 'symmetry', 'Y')
    chip.set('library', libname, 'site', 'unithd', 'size', (0.46,2.72))

    chip.set('library', libname, 'site', 'unithddbl', 'symmetry', 'Y')
    chip.set('library', libname, 'site', 'unithddbl', 'size', (0.46,5.44))

    # lib arch
    chip.set('library', libname, 'arch', libtype)

    # clock buffers
    chip.add('library', libname, 'cells', 'clkbuf', 'sky130_fd_sc_hd__clkbuf_1')

    # hold cells
    chip.add('library', libname, 'cells', 'hold', 'sky130_fd_sc_hd__buf_1')

    # filler
    chip.add('library', libname, 'cells', 'filler', ['sky130_fd_sc_hd__fill_1',
                                                     'sky130_fd_sc_hd__fill_2',
                                                     'sky130_fd_sc_hd__fill_4',
                                                     'sky130_fd_sc_hd__fill_8'])

    # Tapcell
    chip.add('library', libname, 'cells','tapcell', 'sky130_fd_sc_hd__tapvpwrvgnd_1')

    # Endcap
    chip.add('library', libname, 'cells', 'endcap', 'sky130_fd_sc_hd__decap_4')

    chip.add('library', libname, 'cells', 'ignore', [
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
        'sky130_fd_sc_hd__lpflow_lsbuf_lh_isowell_tap_4',
        'sky130_fd_sc_hd__buf_16'
    ])

    # TODO: should probably fill these in, but they're currently unused by
    # OpenROAD flow
    #driver
    chip.add('library', libname, 'cells', 'driver', '')

    # buffer cell
    chip.add('library', libname, 'cells', 'buf', ['sky130_fd_sc_hd__buf_4/A/X'])

    # tie cells
    chip.add('library', libname, 'cells', 'tie', ['sky130_fd_sc_hd__conb_1/HI',
                                                  'sky130_fd_sc_hd__conb_1/LO'])
