
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

    chip = siliconcompiler.Chip()
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
    libtype = 'hd'
    node = 130
    # TODO: dummy numbers, only matter for cost estimation
    wafersize = 300
    hscribe = 0.1
    vscribe = 0.1
    edgemargin = 2

    pdkdir = os.path.join('..', 'third_party', 'pdks', foundry, process, 'pdk', rev)

    #if you are calling this file, you are in asic mode
    chip.set('mode','asic', clobber = True)

    # process name
    chip.set('pdk','foundry', foundry)
    chip.set('pdk','process', process)
    chip.set('pdk','node', node)
    chip.set('pdk','version', rev)
    chip.set('pdk','stackup', stackup)
    chip.set('pdk','wafersize', wafersize)
    chip.set('pdk','edgemargin', edgemargin)
    chip.set('pdk','hscribe', hscribe)
    chip.set('pdk','vscribe', vscribe)

    # Values chosen based on
    # https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/59ad47a1325239b578bf1c2b3cf6617e44d05d47/flow/platforms/sky130hd/tapcell.tcl
    chip.set('pdk','tapmax', 14)
    chip.set('pdk','tapoffset', 2)

    # Tech file
    for tool in ('openroad', 'klayout', 'magic'):
        chip.set('pdk','aprtech',tool,stackup, libtype,'lef',
                 pdkdir+'/apr/sky130_fd_sc_hd.tlef')

    # DRC Runsets
    chip.set('pdk','drc','magic', stackup, 'runset', pdkdir+'/setup/magic/sky130A.tech')

    # LVS Runsets
    chip.set('pdk','lvs','netgen', stackup, 'runset', pdkdir+'/setup/netgen/lvs_setup.tcl')

    # Layer map
    chip.set('pdk','layermap','klayout',stackup, 'def', 'gds', pdkdir+'/setup/klayout/skywater130.lyt')

    # Routing Grid Definitions

    # TODO: what should the SC-internal name of the LI layer be?
    chip.set('pdk','grid', stackup, 'li1', 'name', 'li1')
    chip.set('pdk','grid', stackup, 'li1', 'xoffset', 0.23)
    chip.set('pdk','grid', stackup, 'li1', 'xpitch',  0.46)
    chip.set('pdk','grid', stackup, 'li1', 'yoffset', 0.17)
    chip.set('pdk','grid', stackup, 'li1', 'ypitch',  0.34)
    chip.set('pdk','grid', stackup, 'li1', 'adj', 1.0)

    chip.set('pdk','grid', stackup, 'met1', 'name', 'm1')
    chip.set('pdk','grid', stackup, 'met1', 'xoffset', 0.17)
    chip.set('pdk','grid', stackup, 'met1', 'xpitch',  0.34)
    chip.set('pdk','grid', stackup, 'met1', 'yoffset', 0.17)
    chip.set('pdk','grid', stackup, 'met1', 'ypitch',  0.34)
    chip.set('pdk','grid', stackup, 'met1', 'adj', 0.5)

    chip.set('pdk','grid', stackup, 'met2', 'name', 'm2')
    chip.set('pdk','grid', stackup, 'met2', 'xoffset', 0.23)
    chip.set('pdk','grid', stackup, 'met2', 'xpitch',  0.46)
    chip.set('pdk','grid', stackup, 'met2', 'yoffset', 0.23)
    chip.set('pdk','grid', stackup, 'met2', 'ypitch',  0.46)
    chip.set('pdk','grid', stackup, 'met2', 'adj', 0.5)

    chip.set('pdk','grid', stackup, 'met3', 'name', 'm3')
    chip.set('pdk','grid', stackup, 'met3', 'xoffset', 0.34)
    chip.set('pdk','grid', stackup, 'met3', 'xpitch',  0.68)
    chip.set('pdk','grid', stackup, 'met3', 'yoffset', 0.34)
    chip.set('pdk','grid', stackup, 'met3', 'ypitch',  0.68)
    chip.set('pdk','grid', stackup, 'met3', 'adj', 0.5)

    chip.set('pdk','grid', stackup, 'met4', 'name', 'm4')
    chip.set('pdk','grid', stackup, 'met4', 'xoffset', 0.46)
    chip.set('pdk','grid', stackup, 'met4', 'xpitch',  0.92)
    chip.set('pdk','grid', stackup, 'met4', 'yoffset', 0.46)
    chip.set('pdk','grid', stackup, 'met4', 'ypitch',  0.92)
    chip.set('pdk','grid', stackup, 'met4', 'adj', 0.5)

    chip.set('pdk','grid', stackup, 'met5', 'name', 'm5')
    chip.set('pdk','grid', stackup, 'met5', 'xoffset', 1.7)
    chip.set('pdk','grid', stackup, 'met5', 'xpitch',  3.4)
    chip.set('pdk','grid', stackup, 'met5', 'yoffset', 1.7)
    chip.set('pdk','grid', stackup, 'met5', 'ypitch',  3.4)
    chip.set('pdk','grid', stackup, 'met5', 'adj', 0.5)

#########################
if __name__ == "__main__":

    chip = make_docs()
    chip.writecfg('skywater130.json')
