import os
import sys
import re
import siliconcompiler

def make_docs():
    '''
    The asap7 PDK was developed at ASU in collaboration with ARM Research.
    With funding from the DARPA IDEA program, the PDK was released
    a permissive open source PDK in 2021. The PDK contains SPICE-compatible
    FinFET device models (BSIM-CMG), Technology files for Cadence Virtuoso,
    Design Rule Checker (DRC), Layout vs Schematic Checker (LVS) and
    Extraction Deck for the 7nm technology node. For more details regarding
    the technical specifications of the PDK, please refer the PDK
    documentation and associated publication. Note that this process
    design kit is provided as an academic and research aid only and the
    resulting designs are not manufacturable.

    PDK content:

    * open source DRM
    * device primitive library (virtuoso)
    * spice (hspice)
    * extraction runsets (calibre)
    * drc runsets (calibre)
    * APR technology files
    * 7.5 track multi-vt standard cell libraries

    More information:

    * http://asap.asu.edu/asap
    * L.T. Clark, V. Vashishtha, L. Shifren, A. Gujja, S. Sinha, B. Cline,
      C. Ramamurthya, and G. Yeric, “ASAP7: A 7-nm FinFET Predictive Process
      Design Kit,” Microelectronics Journal, vol. 53, pp. 105-115, July 2016.


    Sources: https://github.com/The-OpenROAD-Project/asap

    .. warning::
       Work in progress (not ready for use)

    '''

    chip = siliconcompiler.Chip()
    setup(chip)

    return chip

def setup(chip):
    '''
    TODO: Add process information
    '''

    foundry = 'virtual'
    process = 'asap7'
    node = 7
    rev = 'r1p7'
    stackup = '10M'
    libtype = '7p5t'
    pdkdir = os.path.join('..', 'third_party', 'pdks', foundry, process, 'pdk', rev)

    # If you got here,  you are in asic mode
    chip.set('mode', 'asic', clobber=True)

    # process name
    chip.set('pdk','foundry', foundry)
    chip.set('pdk','process', process)
    chip.set('pdk','node', node)
    chip.set('pdk','version', rev)
    chip.set('pdk','stackup', stackup)
    chip.set('pdk','tapmax', 25)
    chip.set('pdk','tapoffset', 0)

    # APR tech file
    for tool in ('openroad', 'klayout', 'magic'):
        chip.set('pdk','aprtech', tool, stackup, libtype, 'lef',
                 pdkdir+'/apr/asap7_tech.lef')

    # Openroad APR setup files
    chip.set('pdk', 'aprtech', 'openroad', stackup, libtype, 'tracks',
             pdkdir + '/apr/openroad_tracks.tcl')
    chip.set('pdk', 'aprtech', 'openroad', stackup, libtype, 'tapcells',
             pdkdir + '/apr/openroad_tapcells.tcl')

    # Klayout setup file
    chip.set('pdk','layermap','klayout',stackup, 'def', 'gds',
             pdkdir+'/setup/klayout/asap7.lyt')

    # Routing Grid Definitions
    for layer, sc_name in [('M1', 'm1')]:
        chip.set('pdk','grid', stackup, layer, 'name', sc_name)
        chip.set('pdk','grid', stackup, layer, 'xpitch',  0.036)
        chip.set('pdk','grid', stackup, layer, 'ypitch',  0.036)
        chip.set('pdk','grid', stackup, layer, 'adj',     1.0)

    for layer, sc_name in [('M2', 'm2')]:
        chip.set('pdk','grid', stackup, layer, 'name', sc_name)
        chip.set('pdk','grid', stackup, layer, 'xpitch',  0.036)
        chip.set('pdk','grid', stackup, layer, 'ypitch',  0.027)
        chip.set('pdk','grid', stackup, layer, 'adj',     0.8)

    for layer, sc_name in [('M3', 'm3')]:
        chip.set('pdk','grid', stackup, layer, 'name', sc_name)
        chip.set('pdk','grid', stackup, layer, 'xpitch',  0.036)
        chip.set('pdk','grid', stackup, layer, 'ypitch',  0.036)
        chip.set('pdk','grid', stackup, layer, 'adj',     0.7)

    for layer, sc_name in [('M4', 'm4')]:
        chip.set('pdk','grid', stackup, layer, 'name', sc_name)
        chip.set('pdk','grid', stackup, layer, 'xpitch',  0.036)
        chip.set('pdk','grid', stackup, layer, 'ypitch',  0.048)
        chip.set('pdk','grid', stackup, layer, 'adj',     0.4)

    for layer, sc_name in [('M5', 'm5')]:
        chip.set('pdk','grid', stackup, layer, 'name', sc_name)
        chip.set('pdk','grid', stackup, layer, 'xpitch',  0.048)
        chip.set('pdk','grid', stackup, layer, 'ypitch',  0.048)
        chip.set('pdk','grid', stackup, layer, 'adj',     0.4)

    for layer, sc_name in [('M6', 'm6')]:
        chip.set('pdk','grid', stackup, layer, 'name', sc_name)
        chip.set('pdk','grid', stackup, layer, 'xpitch',  0.048)
        chip.set('pdk','grid', stackup, layer, 'ypitch',  0.064)
        chip.set('pdk','grid', stackup, layer, 'adj',     0.4)

    for layer, sc_name in [('M7', 'm7')]:
        chip.set('pdk','grid', stackup, layer, 'name', sc_name)
        chip.set('pdk','grid', stackup, layer, 'xpitch',  0.064)
        chip.set('pdk','grid', stackup, layer, 'ypitch',  0.064)
        chip.set('pdk','grid', stackup, layer, 'adj',     0.4)

    for layer, sc_name in [('M8', 'm8'), ('M9', 'm9')]:
        chip.set('pdk','grid', stackup, layer, 'name', sc_name)
        chip.set('pdk','grid', stackup, layer, 'xpitch',  0.08)
        chip.set('pdk','grid', stackup, layer, 'ypitch',  0.08)
        chip.set('pdk','grid', stackup, layer, 'adj',     0.4)

#########################
if __name__ == "__main__":

    chip = make_docs()
    chip.writecfg('asap7.json')
