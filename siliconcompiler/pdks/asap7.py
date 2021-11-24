import os
import sys
import re
import siliconcompiler

############################################################################
# DOCS
############################################################################

def make_docs():
    '''
    The asap7 PDK was developed at ASU in collaboration with ARM Research.
    With funding from the DARPA IDEA program, the PDK was released
    a permissive open source PDK in 2021. The PDK contains SPICE-compatible
    FinFET device models (BSIM-CMG), Technology files for Cadence Virtuoso,
    Design Rule Checker (DRC), Layout vs Schematic Checker (LVS) and
    Extraction Deck for the 7nm technology node. For more details regarding
    the technical specifications of the PDK, please refer the PDK
    documentation and associated publication. Please note that this process
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
    setup_pdk(chip)

    return chip


####################################################
# PDK Setup
####################################################

def setup_pdk(chip):
    '''
    TODO: Add process information
    '''

    ###############################################
    # Process
    ###############################################

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
    chip.set('pdk','version', rev)
    chip.set('pdk','stackup', stackup)
    chip.set('pdk','tapmax', 25)
    chip.set('pdk','tapoffset', 0)

    # APR tech file
    chip.set('pdk','aprtech',stackup, libtype, 'lef',
             pdkdir+'/apr/asap7_tech.lef')

    # Routing Grid Definitions
    for sc_name, pdk_name in [('m1', 'M1')]:
        chip.set('pdk','grid', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','grid', stackup, sc_name, 'xoffset', 0.036)
        chip.set('pdk','grid', stackup, sc_name, 'xpitch',  0.036)
        chip.set('pdk','grid', stackup, sc_name, 'yoffset', 0.036)
        chip.set('pdk','grid', stackup, sc_name, 'ypitch',  0.036)
        chip.set('pdk','grid', stackup, sc_name, 'adj',     1.0)

    for sc_name, pdk_name in [('m2', 'M2')]:
        chip.set('pdk','grid', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','grid', stackup, sc_name, 'xoffset', 0.018)
        chip.set('pdk','grid', stackup, sc_name, 'xpitch',  0.036)
        chip.set('pdk','grid', stackup, sc_name, 'yoffset', 0.00)
        chip.set('pdk','grid', stackup, sc_name, 'ypitch',  0.027)
        chip.set('pdk','grid', stackup, sc_name, 'adj',     0.8)

    for sc_name, pdk_name in [('m3', 'M3')]:
        chip.set('pdk','grid', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','grid', stackup, sc_name, 'xoffset', 0.018)
        chip.set('pdk','grid', stackup, sc_name, 'xpitch',  0.036)
        chip.set('pdk','grid', stackup, sc_name, 'yoffset', 0.018)
        chip.set('pdk','grid', stackup, sc_name, 'ypitch',  0.036)
        chip.set('pdk','grid', stackup, sc_name, 'adj',     0.7)

    for sc_name, pdk_name in [('m4', 'M4')]:
        chip.set('pdk','grid', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','grid', stackup, sc_name, 'xoffset', 0.028)
        chip.set('pdk','grid', stackup, sc_name, 'xpitch',  0.036)
        chip.set('pdk','grid', stackup, sc_name, 'yoffset', 0.069)
        chip.set('pdk','grid', stackup, sc_name, 'ypitch',  0.048)
        chip.set('pdk','grid', stackup, sc_name, 'adj',     0.4)

    for sc_name, pdk_name in [('m5', 'M5')]:
        chip.set('pdk','grid', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','grid', stackup, sc_name, 'xoffset', 0.040)
        chip.set('pdk','grid', stackup, sc_name, 'xpitch',  0.048)
        chip.set('pdk','grid', stackup, sc_name, 'yoffset', 0.069)
        chip.set('pdk','grid', stackup, sc_name, 'ypitch',  0.048)
        chip.set('pdk','grid', stackup, sc_name, 'adj',     0.4)


    for sc_name, pdk_name in [('m6', 'M6')]:
        chip.set('pdk','grid', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','grid', stackup, sc_name, 'xoffset', 0.030)
        chip.set('pdk','grid', stackup, sc_name, 'xpitch',  0.048)
        chip.set('pdk','grid', stackup, sc_name, 'yoffset', 0.082)
        chip.set('pdk','grid', stackup, sc_name, 'ypitch',  0.064)
        chip.set('pdk','grid', stackup, sc_name, 'adj',     0.4)

    for sc_name, pdk_name in [('m7', 'M7')]:
        chip.set('pdk','grid', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','grid', stackup, sc_name, 'xoffset', 0.082)
        chip.set('pdk','grid', stackup, sc_name, 'xpitch',  0.064)
        chip.set('pdk','grid', stackup, sc_name, 'yoffset', 0.036)
        chip.set('pdk','grid', stackup, sc_name, 'ypitch',  0.064)
        chip.set('pdk','grid', stackup, sc_name, 'adj',     0.4)

    for sc_name, pdk_name in [('m8', 'M8'), ('m9', 'M9')]:
        chip.set('pdk','grid', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','grid', stackup, sc_name, 'xoffset', 0.098)
        chip.set('pdk','grid', stackup, sc_name, 'xpitch',  0.08)
        chip.set('pdk','grid', stackup, sc_name, 'yoffset', 0.098)
        chip.set('pdk','grid', stackup, sc_name, 'ypitch',  0.08)
        chip.set('pdk','grid', stackup, sc_name, 'adj',     0.4)

    ###############################################
    # Libraries
    ###############################################

    libname = 'asap7sc7p5t_rvt'
    libtype = '7p5t'
    rev = 'r1p7'
    corner = 'typical'
    objectives = ['setup']
    libdir = os.path.join('..', 'third_party', 'pdks', foundry, process, 'libs', libname, rev)

    # rev
    chip.set('library',libname, 'package', 'version',rev)

    # timing
    chip.add('library', libname, 'nldm', corner, 'lib',
             libdir+'/nldm/'+libname+'_ff.lib')

    # lef
    chip.add('library',libname,'lef',
             libdir+'/lef/'+libname+'.lef')
    # gds
    chip.add('library',libname,'gds',
             libdir+'/gds/'+libname+'.gds')
    # site name
    chip.set('library',libname,'site', 'asap7sc7p5t')

    # lib arch
    chip.set('library',libname,'arch',libtype)

    #driver
    chip.add('library',libname,'driver', "BUFx2_ASAP7_75t_R")

    # clock buffers
    chip.add('library',libname,'cells','clkbuf', "BUFx2_ASAP7_75t_R")

    # tie cells
    chip.add('library',libname,'cells','tie', ["TIEHIx1_ASAP7_75t_R/H",
                                               "TIELOx1_ASAP7_75t_R/L"])


    # hold cells
    chip.add('library',libname,'cells','hold', "BUFx2_ASAP7_75t_R")

    # filler
    chip.add('library',libname,'cells','filler', ["FILLER_ASAP7_75t_R"])

    # Stupid small cells
    chip.add('library',libname,'cells','ignore', [
        "*x1_ASAP7*", "*x1p*_ASAP7*", "*xp*_ASAP7*",
        "SDF*", "ICG*", "DFFH*",
    ])

    # Tapcell
    chip.add('library',libname,'cells','tapcell', "TAPCELL_ASAP7_75t_R")

    # Endcap
    chip.add('library',libname,'cells','endcap', "DECAPx1_ASAP7_75t_R")

    ###############################################
    # Methodology
    ###############################################

    chip.set('asic', 'stackup', chip.get('pdk', 'stackup')[0])
    chip.add('asic', 'targetlib', libname)
    chip.set('asic', 'minlayer', "m2")
    chip.set('asic', 'maxlayer', "m7")
    chip.set('asic', 'maxfanout', 64)
    chip.set('asic', 'maxlength', 1000)
    chip.set('asic', 'maxslew', 1.5e-9)
    chip.set('asic', 'maxcap', 1e-12)
    chip.set('asic', 'rclayer', 'clk', 'm5')
    chip.set('asic', 'rclayer', 'data', 'm3')
    chip.set('asic', 'hpinlayer', "m4")
    chip.set('asic', 'vpinlayer', "m5")

    # hard coded mcmm settings (only one corner!)
    corner = 'typical'
    chip.set('mcmm','worst','libcorner', corner)
    chip.set('mcmm','worst','pexcorner', corner)
    chip.set('mcmm','worst','mode', 'func')
    chip.add('mcmm','worst','check', ['setup','hold'])

    # Floorplanning defaults for quick experiments
    chip.set('asic', 'density', 10, clobber=False)
    chip.set('asic', 'aspectratio', 1, clobber=False)
    # Least common multiple of std. cell width (0.054) and height (0.270)
    chip.set('asic', 'coremargin', 0.270, clobber=False)

#########################
if __name__ == "__main__":

    chip = make_docs()
    chip.writecfg('asap7.json')
