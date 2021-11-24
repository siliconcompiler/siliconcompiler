
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
    setup_pdk(chip)

    return chip


####################################################
# PDK Setup
####################################################

def setup_pdk(chip):
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
    chip.set('pdk','aprtech',stackup, libtype, 'lef',pdkdir+'/apr/freepdk45.tech.lef')

    # Klayout setup file
    chip.set('pdk','layermap',stackup, 'def', 'gds', pdkdir+'/setup/klayout/freepdk45.lyt')

    # Routing Grid Definitions
    for sc_name, pdk_name in [('m1', 'metal1')]:
        chip.set('pdk','grid', stackup, sc_name, 'name',    pdk_name)
        chip.set('pdk','grid', stackup, sc_name, 'xoffset', 0.095)
        chip.set('pdk','grid', stackup, sc_name, 'xpitch',  0.19)
        chip.set('pdk','grid', stackup, sc_name, 'yoffset', 0.07)
        chip.set('pdk','grid', stackup, sc_name, 'ypitch',  0.14)
        chip.set('pdk','grid', stackup, sc_name, 'adj',     1.0)

    for sc_name, pdk_name in [('m2', 'metal2')]:
        chip.set('pdk','grid', stackup, sc_name, 'name',    pdk_name)
        chip.set('pdk','grid', stackup, sc_name, 'xoffset', 0.095)
        chip.set('pdk','grid', stackup, sc_name, 'xpitch',  0.19)
        chip.set('pdk','grid', stackup, sc_name, 'yoffset', 0.07)
        chip.set('pdk','grid', stackup, sc_name, 'ypitch',  0.14)
        chip.set('pdk','grid', stackup, sc_name, 'adj',     0.8)

    for sc_name, pdk_name in [('m3', 'metal3')]:
        chip.set('pdk','grid', stackup, sc_name, 'name',    pdk_name)
        chip.set('pdk','grid', stackup, sc_name, 'xoffset', 0.095)
        chip.set('pdk','grid', stackup, sc_name, 'xpitch',  0.19)
        chip.set('pdk','grid', stackup, sc_name, 'yoffset', 0.07)
        chip.set('pdk','grid', stackup, sc_name, 'ypitch',  0.14)
        chip.set('pdk','grid', stackup, sc_name, 'adj',     0.7)

    for sc_name, pdk_name in [('m4', 'metal4'), ('m5', 'metal5'), ('m6', 'metal6')]:
        chip.set('pdk','grid', stackup, sc_name, 'name',    pdk_name)
        chip.set('pdk','grid', stackup, sc_name, 'xoffset', 0.095)
        chip.set('pdk','grid', stackup, sc_name, 'xpitch',  0.28)
        chip.set('pdk','grid', stackup, sc_name, 'yoffset', 0.07)
        chip.set('pdk','grid', stackup, sc_name, 'ypitch',  0.28)
        chip.set('pdk','grid', stackup, sc_name, 'adj',     0.4)

    for sc_name, pdk_name in [('m7', 'metal7'), ('m8', 'metal8')]:
        chip.set('pdk','grid', stackup, sc_name, 'name',    pdk_name)
        chip.set('pdk','grid', stackup, sc_name, 'xoffset', 0.095)
        chip.set('pdk','grid', stackup, sc_name, 'xpitch',  0.8)
        chip.set('pdk','grid', stackup, sc_name, 'yoffset', 0.07)
        chip.set('pdk','grid', stackup, sc_name, 'ypitch',  0.8)
        chip.set('pdk','grid', stackup, sc_name, 'adj',     0.4)

    for sc_name, pdk_name in [('m9', 'metal9'), ('m10', 'metal10')]:
        chip.set('pdk','grid', stackup, sc_name, 'name',    pdk_name)
        chip.set('pdk','grid', stackup, sc_name, 'xoffset', 0.095)
        chip.set('pdk','grid', stackup, sc_name, 'xpitch',  1.6)
        chip.set('pdk','grid', stackup, sc_name, 'yoffset', 0.07)
        chip.set('pdk','grid', stackup, sc_name, 'ypitch',  1.6)
        chip.set('pdk','grid', stackup, sc_name, 'adj',     0.4)

    ###############################################
    # Libraries
    ###############################################

    libname = 'NangateOpenCellLibrary'
    libtype = '10t'
    rev = 'r1p0'
    corner = 'typical'
    objectives = ['setup']

    libdir = os.path.join('..', 'third_party', 'pdks', foundry, process, 'libs', libname, rev)

    # standard cell typ
    chip.set('library',libname,'type','stdcell')

    # rev
    chip.set('library',libname, 'package', 'version',rev)

    # timing
    chip.add('library',libname, 'nldm', corner, 'lib',
             libdir+'/lib/NangateOpenCellLibrary_typical.lib')

    # lef
    chip.add('library',libname,'lef',
             libdir+'/lef/NangateOpenCellLibrary.macro.mod.lef')
    # gds
    chip.add('library',libname,'gds',
             libdir+'/gds/NangateOpenCellLibrary.gds')
    # site name
    chip.set('library',libname,'site', 'FreePDK45_38x28_10R_NP_162NW_34O')

    # lib arch
    chip.set('library',libname,'arch',libtype)

    #driver
    chip.add('library',libname,'driver', "BUF_X4")

    # clock buffers
    chip.add('library',libname,'cells','clkbuf', "BUF_X4")

    # tie cells
    chip.add('library',libname,'cells','tie', ["LOGIC1_X1/Z",
                                               "LOGIC0_X1/Z"])

    # buffer cell
    chip.add('library', libname, 'cells', 'buf', ['BUF_X1/A/Z'])

    # hold cells
    chip.add('library',libname,'cells','hold', "BUF_X1")

    # filler
    chip.add('library',libname,'cells','filler', ["FILLCELL_X1",
                                                  "FILLCELL_X2",
                                                  "FILLCELL_X4",
                                                  "FILLCELL_X8",
                                                  "FILLCELL_X16",
                                                  "FILLCELL_X32"])

    # Stupid small cells
    chip.add('library',libname,'cells','ignore', ["AOI211_X1",
                                                  "OAI211_X1"])

    # Tapcell
    chip.add('library',libname,'cells','tapcell', "FILLCELL_X1")

    # Endcap
    chip.add('library',libname,'cells','endcap', "FILLCELL_X1")

    ###############################################
    # Methodology
    ###############################################

    chip.set('asic', 'stackup', chip.get('pdk', 'stackup')[0])
    chip.add('asic', 'targetlib', libname)
    chip.set('asic', 'minlayer', "m1")
    chip.set('asic', 'maxlayer', "m10")
    chip.set('asic', 'maxfanout', 64)
    chip.set('asic', 'maxlength', 1000)
    chip.set('asic', 'maxslew', 0.2e-9)
    chip.set('asic', 'maxcap', 0.2e-12)
    chip.set('asic', 'rclayer', 'clk', "m5")
    chip.set('asic', 'rclayer', 'data',"m3")
    chip.set('asic', 'hpinlayer', "m3")
    chip.set('asic', 'vpinlayer', "m2")

    corner = 'typical'
    # hard coded mcmm settings (only one corner!)
    chip.set('mcmm','worst','libcorner', corner)
    chip.set('mcmm','worst','pexcorner', corner)
    chip.set('mcmm','worst','mode', 'func')
    chip.set('mcmm','worst','check', ['setup','hold'])

    # Floorplanning defaults for quick experiments
    chip.set('asic', 'density', 10, clobber=False)
    chip.set('asic', 'aspectratio', 1, clobber=False)
    # 10 track core margin
    chip.set('asic', 'coremargin', 1.9, clobber=False)

#########################
if __name__ == "__main__":

    chip = make_docs()
    chip.writecfg('freepdk45.json')
