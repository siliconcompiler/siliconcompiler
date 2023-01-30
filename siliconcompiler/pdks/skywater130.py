
import os
import sys
import re
import siliconcompiler

############################################################################
# DOCS
############################################################################

def make_docs():
    '''
    The 'skywater130' Open Source PDK is a collaboration between Google and
    SkyWater Technology Foundry to provide a fully open source Process
    Design Kit and related resources, which can be used to create
    manufacturable designs at SkyWater’s facility.

    Skywater130 Process Highlights:
    * 130nm process
    * support for internal 1.8V with 5.0V I/Os (operable at 2.5V)
    * 1 level of local interconnect
    * 5 levels of metal

    PDK content:
    * An open source design rule manual
    * multiple standard digital cell libraries
    * primitive cell libraries and models for creating analog designs
    * EDA support files for multiple open source and proprietary flows

    More information:
    * https://skywater-pdk.readthedocs.io/en/latest/

    Sources:
    * https://github.com/google/skywater-pdk

    '''

    chip = siliconcompiler.Chip('skywater130')
    setup(chip)

    return chip

####################################################
# PDK Setup
####################################################

def setup(chip):
    '''
    Setup function for the skywater130 PDK.
    '''

    foundry = 'skywater'
    process = 'skywater130'
    rev = 'v0_0_2'
    stackup = '5M1LI'

    # TODO: eventualy support hs libtype as well
    libtype = 'unithd'
    node = 130
    # TODO: dummy numbers, only matter for cost estimation
    wafersize = 300
    hscribe = 0.1
    vscribe = 0.1
    edgemargin = 2

    pdkdir = os.path.join('..', 'third_party', 'pdks', foundry, process, 'pdk', rev)

    pdk = siliconcompiler.PDK()

    # process name
    pdk.set('pdk', process, 'foundry', foundry)
    pdk.set('pdk', process, 'node', node)
    pdk.set('pdk', process, 'version', rev)
    pdk.set('pdk', process, 'stackup', stackup)
    pdk.set('pdk', process, 'wafersize', wafersize)
    pdk.set('pdk', process, 'edgemargin', edgemargin)
    pdk.set('pdk', process, 'hscribe', hscribe)
    pdk.set('pdk', process, 'vscribe', vscribe)

    # APR Setup
    # TODO: remove libtype
    for tool in ('openroad', 'klayout', 'magic'):
        pdk.set('pdk', process,'aprtech',tool,stackup, libtype,'lef',
                 pdkdir+'/apr/sky130_fd_sc_hd.tlef')

    pdk.set('pdk', process, 'minlayer', stackup, 'met1')
    pdk.set('pdk', process, 'maxlayer', stackup, 'met5')

    # DRC Runsets
    pdk.set('pdk', process,'drc', 'runset', 'magic', stackup, 'basic', pdkdir+'/setup/magic/sky130A.tech')

    # LVS Runsets
    pdk.set('pdk', process,'lvs', 'runset', 'netgen', stackup, 'basic', pdkdir+'/setup/netgen/lvs_setup.tcl')

    # Layer map and display file
    pdk.set('pdk', process, 'layermap', 'klayout', 'def', 'gds', stackup, pdkdir+'/setup/klayout/skywater130.lyt')
    pdk.set('pdk', process, 'display', 'klayout', stackup, pdkdir+'/setup/klayout/sky130A.lyp')

    # Openroad global routing grid derating
    openroad_layer_adjustments = {
        'li1': 1.0,
        'met1': 0.5,
        'met2': 0.5,
        'met3': 0.5,
        'met4': 0.5,
        'met5': 0.5,
    }
    for layer, adj in openroad_layer_adjustments.items():
        pdk.set('pdk', process, 'var', 'openroad', f'{layer}_adjustment', stackup, str(adj))

    pdk.set('pdk', process, 'var', 'openroad', 'rclayer_signal', stackup, 'met3')
    pdk.set('pdk', process, 'var', 'openroad', 'rclayer_clock', stackup, 'met4')

    pdk.set('pdk', process, 'var', 'openroad', 'pin_layer_vertical', stackup, 'met2')
    pdk.set('pdk', process, 'var', 'openroad', 'pin_layer_horizontal', stackup, 'met3')

    # PEX
    pdk.set('pdk', process, 'pexmodel', 'openroad', stackup, 'typical',
        pdkdir + '/pex/openroad/typical.tcl')

    return pdk

#########################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest('skywater130.tcl')
