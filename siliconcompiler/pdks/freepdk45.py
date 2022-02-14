
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

    chip = siliconcompiler.Chip()
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

    # If you got here,  you are in asic mode
    chip.set('mode', 'asic', clobber=True)

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
    chip.set('pdk','d0', d0)

    chip.set('pdk','tapmax', 120)
    chip.set('pdk','tapoffset', 2)

    # APR tech file
    for tool in ('openroad', 'klayout', 'magic'):
        chip.set('pdk','aprtech', tool, stackup, libtype, 'lef',
                 pdkdir+'/apr/freepdk45.tech.lef')

    # Klayout setup file
    chip.set('pdk','layermap','klayout',stackup, 'def', 'gds',
             pdkdir+'/setup/klayout/freepdk45.lyt')

    # Routing Grid Definitions
    for layer, sc_name in [('metal1', 'm1')]:
        chip.set('pdk','grid', stackup, layer, 'name',    sc_name)
        chip.set('pdk','grid', stackup, layer, 'xoffset', 0.095)
        chip.set('pdk','grid', stackup, layer, 'xpitch',  0.19)
        chip.set('pdk','grid', stackup, layer, 'yoffset', 0.07)
        chip.set('pdk','grid', stackup, layer, 'ypitch',  0.14)
        chip.set('pdk','grid', stackup, layer, 'adj',     1.0)
        chip.set('pdk','grid', stackup, layer, 'dir',    'horizontal')

    for layer, sc_name in [('metal2', 'm2')]:
        chip.set('pdk','grid', stackup, layer, 'name',    sc_name)
        chip.set('pdk','grid', stackup, layer, 'xoffset', 0.095)
        chip.set('pdk','grid', stackup, layer, 'xpitch',  0.19)
        chip.set('pdk','grid', stackup, layer, 'yoffset', 0.07)
        chip.set('pdk','grid', stackup, layer, 'ypitch',  0.14)
        chip.set('pdk','grid', stackup, layer, 'adj',     0.8)
        chip.set('pdk','grid', stackup, layer, 'dir',    'vertical')

    for layer, sc_name in [('metal3', 'm3')]:
        chip.set('pdk','grid', stackup, layer, 'name',    sc_name)
        chip.set('pdk','grid', stackup, layer, 'xoffset', 0.095)
        chip.set('pdk','grid', stackup, layer, 'xpitch',  0.19)
        chip.set('pdk','grid', stackup, layer, 'yoffset', 0.07)
        chip.set('pdk','grid', stackup, layer, 'ypitch',  0.14)
        chip.set('pdk','grid', stackup, layer, 'adj',     0.7)
        chip.set('pdk','grid', stackup, layer, 'dir',    'horizontal')

    for layer, sc_name in [('metal4', 'm4'), ('metal5', 'm5'), ('metal6', 'm6')]:
        chip.set('pdk','grid', stackup, layer, 'name',    sc_name)
        chip.set('pdk','grid', stackup, layer, 'xoffset', 0.095)
        chip.set('pdk','grid', stackup, layer, 'xpitch',  0.28)
        chip.set('pdk','grid', stackup, layer, 'yoffset', 0.07)
        chip.set('pdk','grid', stackup, layer, 'ypitch',  0.28)
        chip.set('pdk','grid', stackup, layer, 'adj',     0.4)
        if layer in ('metal4', 'metal6'):
            chip.set('pdk','grid', stackup, layer, 'dir', 'vertical')
        else:
            chip.set('pdk','grid', stackup, layer, 'dir', 'horizontal')

    for layer, sc_name in [('metal7', 'm7'), ('metal8', 'm8')]:
        chip.set('pdk','grid', stackup, layer, 'name',    sc_name)
        chip.set('pdk','grid', stackup, layer, 'xoffset', 0.095)
        chip.set('pdk','grid', stackup, layer, 'xpitch',  0.8)
        chip.set('pdk','grid', stackup, layer, 'yoffset', 0.07)
        chip.set('pdk','grid', stackup, layer, 'ypitch',  0.8)
        chip.set('pdk','grid', stackup, layer, 'adj',     0.4)
        if layer in ('metal8'):
            chip.set('pdk','grid', stackup, layer, 'dir', 'vertical')
        else:
            chip.set('pdk','grid', stackup, layer, 'dir', 'horizontal')


    for layer, sc_name in [('metal9', 'm9'), ('metal10', 'm10')]:
        chip.set('pdk','grid', stackup, layer, 'name',    sc_name)
        chip.set('pdk','grid', stackup, layer, 'xoffset', 0.095)
        chip.set('pdk','grid', stackup, layer, 'xpitch',  1.6)
        chip.set('pdk','grid', stackup, layer, 'yoffset', 0.07)
        chip.set('pdk','grid', stackup, layer, 'ypitch',  1.6)
        chip.set('pdk','grid', stackup, layer, 'adj',     0.4)
        if layer in ('metal10'):
            chip.set('pdk','grid', stackup, layer, 'dir', 'vertical')
        else:
            chip.set('pdk','grid', stackup, layer, 'dir', 'horizontal')

#########################
if __name__ == "__main__":

    chip = make_docs()
    chip.writecfg('freepdk45.json')
