
import os
import sys
import re
import siliconcompiler


############################################################################
# DOCS
############################################################################

def make_docs():
    '''
    The freepdk45 PDK is a virtual PDK derived from the work done at
    NCSU (NCSU_TechLib_FreePDK45.)  It supplies techfiles, display
    resources, design rules and scripts to permit layout design and rule
    checking for a generic 45 nanometer process.  The technology information
    contained in this kit has been compiled from published papers,
    predictive technology models and rule scaling.  This information may be
    freely used, modified, and distributed under the open-source Apache
    License (see the file APACHE-LICENSE-2.0.txt in the root install
    directory for the complete text). This technology is intended to work
    with the 45nm BSIM4 Predictive Technology Model from Arizona State
    University (http://www.eas.asu.edu/~ptm).  See the HSPICE Models
    section of this file for details about these models.

    More information:
    * https://www.eda.ncsu.edu/wiki/FreePDK45:Manual

    '''

    chip = siliconcompiler.Chip('freepdk45')
    setup(chip)

    return chip


####################################################
# PDK Setup
####################################################

def setup(chip):
    '''
    Setup function for the freepdk45 PDK.
    '''

    ###############################################
    # Process
    ###############################################

    foundry = 'virtual'
    process = 'freepdk45'
    rev = 'r1p0'
    stackup = '10M'
    libtype = '10t'
    node = 45
    wafersize = 300
    hscribe = 0.1
    vscribe = 0.1
    edgemargin = 2
    d0 = 1.25

    pdkdir = os.path.join('..', 'third_party', 'pdks', foundry, process, 'pdk', rev)

    # process name
    chip.set('pdk', process, 'foundry', foundry)
    chip.set('pdk', process, 'node', node)
    chip.set('pdk', process, 'version', rev)
    chip.set('pdk', process, 'stackup', stackup)
    chip.set('pdk', process, 'wafersize', wafersize)
    chip.set('pdk', process, 'edgemargin', edgemargin)
    chip.set('pdk', process, 'hscribe', hscribe)
    chip.set('pdk', process, 'vscribe', vscribe)
    chip.set('pdk', process, 'd0', d0)

    # APR tech file
    # TODO: remove libtype
    for tool in ('openroad', 'klayout', 'magic'):
        chip.set('pdk', process, 'aprtech', tool, stackup, libtype, 'lef',
                 pdkdir+'/apr/freepdk45.tech.lef')

    # Klayout setup file
    chip.set('pdk', process, 'layermap', 'klayout', 'def', 'gds', stackup,
             pdkdir+'/setup/klayout/freepdk45.lyt')

    chip.set('pdk', process, 'display', 'klayout', stackup,
            pdkdir + '/setup/klayout/freepdk45.lyp')

    # Openroad global routing grid derating
    openroad_layer_adjustments = {
        'metal1': 1.0,
        'metal2': 0.8,
        'metal3': 0.7,
        'metal4': 0.4,
        'metal5': 0.4,
        'metal6': 0.4,
        'metal7': 0.4,
        'metal8': 0.4,
        'metal9': 0.4,
        'metal10': 0.4
    }
    for layer, adj in openroad_layer_adjustments.items():
        chip.set('pdk', process, 'var', 'openroad', f'{layer}_adjustment', stackup, str(adj))

    chip.set('pdk', process, 'var', 'openroad', 'rclayer_signal', stackup, 'metal3')
    chip.set('pdk', process, 'var', 'openroad', 'rclayer_clock', stackup, 'metal5')

    chip.set('pdk', process, 'var', 'openroad', 'pin_layer_vertical', stackup, 'metal2')
    chip.set('pdk', process, 'var', 'openroad', 'pin_layer_horizontal', stackup, 'metal3')

    # PEX
    chip.set('pdk', process, 'pexmodel', 'openroad', stackup, 'typical',
        pdkdir + '/pex/openroad/typical.tcl')

#########################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest('freepdk45.tcl')
