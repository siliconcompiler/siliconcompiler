
import os
import sys
import re
import siliconcompiler
from siliconcompiler.schema import PDKSchema

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

    schema = PDKSchema()

    # TODO: eventualy support hs libtype as well
    libtype = 'unithd'
    node = 130
    # TODO: dummy numbers, only matter for cost estimation
    wafersize = 300
    hscribe = 0.1
    vscribe = 0.1
    edgemargin = 2

    pdkdir = os.path.join('..', 'third_party', 'pdks', foundry, process, 'pdk', rev)

    # process name
    schema.set('pdk', process, 'foundry', foundry)
    schema.set('pdk', process, 'node', node)
    schema.set('pdk', process, 'version', rev)
    schema.set('pdk', process, 'stackup', stackup)
    schema.set('pdk', process, 'wafersize', wafersize)
    schema.set('pdk', process, 'edgemargin', edgemargin)
    schema.set('pdk', process, 'hscribe', hscribe)
    schema.set('pdk', process, 'vscribe', vscribe)

    # APR Setup
    # TODO: remove libtype
    for tool in ('openroad', 'klayout', 'magic'):
        schema.set('pdk', process,'aprtech',tool,stackup, libtype,'lef',
                   pdkdir+'/apr/sky130_fd_sc_hd.tlef')

    schema.set('pdk', process, 'minlayer', stackup, 'met1')
    schema.set('pdk', process, 'maxlayer', stackup, 'met5')

    # DRC Runsets
    schema.set('pdk', process,'drc', 'runset', 'magic', stackup, 'basic', pdkdir+'/setup/magic/sky130A.tech')

    # LVS Runsets
    schema.set('pdk', process,'lvs', 'runset', 'netgen', stackup, 'basic', pdkdir+'/setup/netgen/lvs_setup.tcl')

    # Layer map and display file
    schema.set('pdk', process, 'layermap', 'klayout', 'def', 'gds', stackup, pdkdir+'/setup/klayout/skywater130.lyt')
    schema.set('pdk', process, 'display', 'klayout', stackup, pdkdir+'/setup/klayout/sky130A.lyp')

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
        schema.set('pdk', process, 'var', 'openroad', f'{layer}_adjustment', stackup, str(adj))

    schema.set('pdk', process, 'var', 'openroad', 'rclayer_signal', stackup, 'met3')
    schema.set('pdk', process, 'var', 'openroad', 'rclayer_clock', stackup, 'met4')

    schema.set('pdk', process, 'var', 'openroad', 'pin_layer_vertical', stackup, 'met2')
    schema.set('pdk', process, 'var', 'openroad', 'pin_layer_horizontal', stackup, 'met3')

    # PEX
    schema.set('pdk', process, 'pexmodel', 'openroad', stackup, 'typical',
               pdkdir + '/pex/openroad/typical.tcl')

    return schema

#########################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest('skywater130.tcl')
