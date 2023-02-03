
import os
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

    return setup(chip)


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

    pdk = siliconcompiler.PDK(chip, process)

    # process name
    pdk.set('pdk', process, 'foundry', foundry)
    pdk.set('pdk', process, 'node', node)
    pdk.set('pdk', process, 'version', rev)
    pdk.set('pdk', process, 'stackup', stackup)
    pdk.set('pdk', process, 'wafersize', wafersize)
    pdk.set('pdk', process, 'edgemargin', edgemargin)
    pdk.set('pdk', process, 'hscribe', hscribe)
    pdk.set('pdk', process, 'vscribe', vscribe)
    pdk.set('pdk', process, 'd0', d0)

    # APR Setup
    for tool in ('openroad', 'klayout', 'magic'):
        pdk.set('pdk', process, 'aprtech', tool, stackup, libtype, 'lef',
                pdkdir+'/apr/freepdk45.tech.lef')

    pdk.set('pdk', process, 'minlayer', stackup, 'metal1')
    pdk.set('pdk', process, 'maxlayer', stackup, 'metal10')

    # Klayout setup file
    pdk.set('pdk', process, 'layermap', 'klayout', 'def', 'gds', stackup,
            pdkdir+'/setup/klayout/freepdk45.lyt')

    pdk.set('pdk', process, 'display', 'klayout', stackup,
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
        pdk.set('pdk', process, 'var', 'openroad', f'{layer}_adjustment', stackup, str(adj))

    pdk.set('pdk', process, 'var', 'openroad', 'rclayer_signal', stackup, 'metal3')
    pdk.set('pdk', process, 'var', 'openroad', 'rclayer_clock', stackup, 'metal5')

    pdk.set('pdk', process, 'var', 'openroad', 'pin_layer_vertical', stackup, 'metal2')
    pdk.set('pdk', process, 'var', 'openroad', 'pin_layer_horizontal', stackup, 'metal3')

    # PEX
    pdk.set('pdk', process, 'pexmodel', 'openroad', stackup, 'typical',
        pdkdir + '/pex/openroad/typical.tcl')

    return pdk

#########################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest('freepdk45.tcl')
