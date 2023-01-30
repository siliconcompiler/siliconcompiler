import os
import sys
import re
import siliconcompiler
from siliconcompiler.schema import PDKSchema

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

    chip = siliconcompiler.Chip('asap7')
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
    wafersize = 300
    libtype = '7p5t'
    pdkdir = os.path.join('..', 'third_party', 'pdks', foundry, process, 'pdk', rev)

    schema = PDKSchema()

    # process name
    schema.set('pdk', process, 'foundry', foundry)
    schema.set('pdk', process, 'node', node)
    schema.set('pdk', process, 'wafersize', wafersize)
    schema.set('pdk', process, 'version', rev)
    schema.set('pdk', process, 'stackup', stackup)

    # APR tech file
    for tool in ('openroad', 'klayout', 'magic'):
        schema.set('pdk', process, 'aprtech', tool, stackup, libtype, 'lef',
                 pdkdir+'/apr/asap7_tech.lef')

    schema.set('pdk', process, 'minlayer', stackup, 'M2')
    schema.set('pdk', process, 'maxlayer', stackup, 'M7')

    # Klayout setup file
    schema.set('pdk', process, 'layermap','klayout','def','gds',stackup,
               pdkdir+'/setup/klayout/asap7.lyt')

    # Openroad global routing grid derating
    openroad_layer_adjustments = {
        'M1': 1.0,
        'M2': 0.8,
        'M3': 0.7,
        'M4': 0.4,
        'M5': 0.4,
        'M6': 0.4,
        'M7': 0.4,
        'M8': 0.4,
        'M9': 0.4
    }
    for layer, adj in openroad_layer_adjustments.items():
        schema.set('pdk', process, 'var', 'openroad', f'{layer}_adjustment', stackup, str(adj))

    schema.set('pdk', process, 'var', 'openroad', 'rclayer_signal', stackup, 'M3')
    schema.set('pdk', process, 'var', 'openroad', 'rclayer_clock', stackup, 'M5')

    schema.set('pdk', process, 'var', 'openroad', 'pin_layer_vertical', stackup, 'M5')
    schema.set('pdk', process, 'var', 'openroad', 'pin_layer_horizontal', stackup, 'M4')

    # PEX
    schema.set('pdk', process, 'pexmodel', 'openroad', stackup, 'typical',
               pdkdir + '/pex/openroad/typical.tcl')

    return schema

#########################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest('asap7.tcl')
