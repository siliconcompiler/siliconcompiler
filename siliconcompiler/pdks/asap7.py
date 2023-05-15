import os
import siliconcompiler


####################################################
# PDK Setup
####################################################
def setup(chip):
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

    * https://asap.asu.edu/
    * L.T. Clark, V. Vashishtha, L. Shifren, A. Gujja, S. Sinha, B. Cline,
      C. Ramamurthya, and G. Yeric, “ASAP7: A 7-nm FinFET Predictive Process
      Design Kit,” Microelectronics Journal, vol. 53, pp. 105-115, July 2016.


    Sources: https://github.com/The-OpenROAD-Project/asap7

    .. warning::
       Work in progress (not ready for use)
    '''

    foundry = 'virtual'
    process = 'asap7'
    node = 7
    rev = 'r1p7'
    stackup = '10M'
    wafersize = 300
    libtype = '7p5t'
    pdkdir = os.path.join('..', 'third_party', 'pdks', foundry, process, 'pdk', rev)

    pdk = siliconcompiler.PDK(chip, process)

    # process name
    pdk.set('pdk', process, 'foundry', foundry)
    pdk.set('pdk', process, 'node', node)
    pdk.set('pdk', process, 'wafersize', wafersize)
    pdk.set('pdk', process, 'version', rev)
    pdk.set('pdk', process, 'stackup', stackup)

    # APR tech file
    for tool in ('openroad', 'klayout', 'magic'):
        pdk.set('pdk', process, 'aprtech', tool, stackup, libtype, 'lef',
                pdkdir + '/apr/asap7_tech.lef')

    pdk.set('pdk', process, 'minlayer', stackup, 'M2')
    pdk.set('pdk', process, 'maxlayer', stackup, 'M7')

    # Klayout setup file
    pdk.set('pdk', process, 'layermap', 'klayout', 'def', 'klayout', stackup,
            pdkdir + '/setup/klayout/asap7.lyt')

    pdk.set('pdk', process, 'display', 'klayout', stackup,
            pdkdir + '/setup/klayout/asap7.lyp')

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
        'M9': 0.4,
        'Pad': 1.0
    }
    for layer, adj in openroad_layer_adjustments.items():
        pdk.set('pdk', process, 'var', 'openroad', f'{layer}_adjustment', stackup, str(adj))

    pdk.set('pdk', process, 'var', 'openroad', 'rclayer_signal', stackup, 'M3')
    pdk.set('pdk', process, 'var', 'openroad', 'rclayer_clock', stackup, 'M3')

    pdk.set('pdk', process, 'var', 'openroad', 'pin_layer_vertical', stackup, 'M5')
    pdk.set('pdk', process, 'var', 'openroad', 'pin_layer_horizontal', stackup, 'M4')

    # PEX
    pdk.set('pdk', process, 'pexmodel', 'openroad', stackup, 'typical',
            pdkdir + '/pex/openroad/typical.tcl')
    pdk.set('pdk', process, 'pexmodel', 'openroad-openrcx', stackup, 'typical',
            pdkdir + '/pex/openroad/typical.rules')

    return pdk


#########################
if __name__ == "__main__":
    pdk = setup(siliconcompiler.Chip('<pdk>'))
    pdk.write_manifest(f'{pdk.top()}.json')
