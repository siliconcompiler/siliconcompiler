
import os
import sys
import re
import siliconcompiler

####################################################
# PDK Setup
####################################################

def setup_platform(chip):

    foundry = 'virtual'
    process = 'freepdk45'
    rev = 'r1p0'
    stackup = '10M'
    libtype = '10t'
    node = '45'
    wafersize = '300'
    hscribe = '0.1'
    vscribe = '0.1'
    edgemargin = '2'
    d0 = '1.25'
    
    pdkdir = '/'.join(["asic",
                       foundry,
                       process,
                       'pdk',
                       rev])
    

    #if you are calling this file, you are in asic mode
    chip.set('mode','asic')

    # process name
    chip.set('pdk','foundry', foundry)
    chip.set('pdk','process', process)
    chip.set('pdk','node', node)
    chip.set('pdk','rev', rev)
    chip.set('pdk','stackup', stackup)
    chip.set('pdk','wafersize', wafersize)
    chip.set('pdk','edgemargin', edgemargin)
    chip.set('pdk','hscribe', hscribe)
    chip.set('pdk','vscribe', vscribe)
    chip.set('pdk','d0', d0)

    chip.set('pdk','tapmax', "120")
    chip.set('pdk','tapoffset', "0")

    # APR tech file
    chip.set('pdk','aprtech',stackup, libtype, 'openroad',
             pdkdir+'/apr/freepdk45.tech.lef')

    # Routing Grid Definitions
    for sc_name, pdk_name in [('m1', 'metal1'), ('m3', 'metal3')]:
        chip.set('pdk','aprlayer', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','aprlayer', stackup, sc_name, 'xoffset', '0.095')
        chip.set('pdk','aprlayer', stackup, sc_name, 'xpitch',  '0.19')
        chip.set('pdk','aprlayer', stackup, sc_name, 'yoffset', '0.07')
        chip.set('pdk','aprlayer', stackup, sc_name, 'ypitch',  '0.14')

    for sc_name, pdk_name in [('m2', 'metal2')]:
        chip.set('pdk','aprlayer', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','aprlayer', stackup, sc_name, 'xoffset', '0.095')
        chip.set('pdk','aprlayer', stackup, sc_name, 'xpitch',  '0.19')
        chip.set('pdk','aprlayer', stackup, sc_name, 'yoffset', '0.07')
        chip.set('pdk','aprlayer', stackup, sc_name, 'ypitch',  '0.14')

    for sc_name, pdk_name in [('m4', 'metal4'), ('m5', 'metal5'), ('m6', 'metal6')]:
        chip.set('pdk','aprlayer', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','aprlayer', stackup, sc_name, 'xoffset', '0.095')
        chip.set('pdk','aprlayer', stackup, sc_name, 'xpitch',  '0.28')
        chip.set('pdk','aprlayer', stackup, sc_name, 'yoffset', '0.07')
        chip.set('pdk','aprlayer', stackup, sc_name, 'ypitch',  '0.28')

    for sc_name, pdk_name in [('m7', 'metal7'), ('m8', 'metal8')]:
        chip.set('pdk','aprlayer', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','aprlayer', stackup, sc_name, 'xoffset', '0.095')
        chip.set('pdk','aprlayer', stackup, sc_name, 'xpitch',  '0.8')
        chip.set('pdk','aprlayer', stackup, sc_name, 'yoffset', '0.07')
        chip.set('pdk','aprlayer', stackup, sc_name, 'ypitch',  '0.8')

    for sc_name, pdk_name in [('m9', 'metal9'), ('m10', 'metal10')]:
        chip.set('pdk','aprlayer', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','aprlayer', stackup, sc_name, 'xoffset', '0.095')
        chip.set('pdk','aprlayer', stackup, sc_name, 'xpitch',  '1.6')
        chip.set('pdk','aprlayer', stackup, sc_name, 'yoffset', '0.07')
        chip.set('pdk','aprlayer', stackup, sc_name, 'ypitch',  '1.6')

####################################################
# Library Setup
####################################################
def setup_libs(chip, vendor=None):
 
    foundry = 'virtual'
    process = 'freepdk45'
    libname = 'NangateOpenCellLibrary'
    libtype = '10t'
    libwidth = '0.19'
    libheight = '1.4'
    rev = 'r1p0'
    corner = 'typical'
    objectives = ['setup']
    libdir = '/'.join(["asic",
                       foundry,
                       process,
                       'libs',
                       libname,
                       rev])
    
    # rev
    chip.set('stdcell',libname,'rev',rev)    

    # timing
    chip.set('stdcell',libname, 'model', corner, 'nldm', 'lib',
             libdir+'/lib/NangateOpenCellLibrary_typical.lib')

    # lef
    chip.set('stdcell',libname,'lef',
             libdir+'/lef/NangateOpenCellLibrary.macro.mod.lef')    
    # gds
    chip.set('stdcell',libname,'gds',
             libdir+'/gds/NangateOpenCellLibrary.gds')
    # site name
    chip.set('stdcell',libname,'site', 'FreePDK45_38x28_10R_NP_162NW_34O')
    # lib arch
    chip.set('stdcell',libname,'libtype',libtype)

    # lib site/tile/size
    chip.set('stdcell',libname,'width', libwidth)
    chip.set('stdcell',libname,'height', libheight)

    #driver
    chip.add('stdcell',libname,'driver', "BUF_X4")
    
    # clock buffers
    chip.add('stdcell',libname,'cells','clkbuf', "BUF_X4")

    # tie cells
    chip.add('stdcell',libname,'cells','tie', ["LOGIC1_X1",
                                               "LOGIC0_X1"])


    # hold cells
    chip.add('stdcell',libname,'cells','hold', "BUF_X1")

    # filler
    chip.add('stdcell',libname,'cells','filler', ["FILLCELL_X1",
                                                  "FILLCELL_X2",
                                                  "FILLCELL_X4",
                                                  "FILLCELL_X8",
                                                  "FILLCELL_X16",
                                                  "FILLCELL_X32"])
    
    # Stupid small cells
    chip.add('stdcell',libname,'cells','ignore', ["AOI211_X1",
                                                  "OAI211_X1"])

    # Tapcell
    chip.add('stdcell',libname,'cells','tapcell', "FILLCELL_X1")

    # Endcap
    chip.add('stdcell',libname,'cells','endcap', "FILLCELL_X1")

        
#########################
def setup_design(chip):

    chip.set('asic', 'stackup', chip.get('pdk', 'stackup')[0])
    chip.set('asic', 'targetlib', chip.getkeys('stdcell'))
    chip.set('asic', 'minlayer', "m1")
    chip.set('asic', 'maxlayer', "m10")
    chip.set('asic', 'maxfanout', "64")
    chip.set('asic', 'maxlength', "1000")
    chip.set('asic', 'maxslew', "0.2e-9")
    chip.set('asic', 'maxcap', "0.2e-12")
    chip.set('asic', 'clklayer', "m5")
    chip.set('asic', 'rclayer', "m3")
    chip.set('asic', 'hpinlayer', "m3")
    chip.set('asic', 'vpinlayer', "m2")
    chip.set('asic', 'density', "1.0")

    corner = 'typical'
    # hard coded mcmm settings (only one corner!)
    chip.set('mcmm','worst','libcorner', corner)
    chip.set('mcmm','worst','pexcorner', corner)
    chip.set('mcmm','worst','mode', 'func')
    chip.set('mcmm','worst','check', ['setup','hold'])
    
#########################
if __name__ == "__main__":    

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_platform(chip)
    setup_libs(chip)
    # write out result
    chip.writecfg(output)

   
