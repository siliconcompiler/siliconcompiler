import os
import sys
import re
import siliconcompiler

####################################################
# PDK Setup
####################################################

def setup_platform(chip):

    foundry = 'virtual'
    process = 'asap7'
    node = '7'
    rev = 'r1p0'
    stackup = '10M'
    libtype = '10t'
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
    chip.set('pdk','rev', rev)
    chip.set('pdk','stackup', stackup)
    chip.set('pdk','tapmax', "120")
    chip.set('pdk','tapoffset', "0")

    # APR tech file
    chip.set('pdk','aprtech',stackup, libtype, 'openroad',
             pdkdir+'/apr/freepdk45.tech.lef')

    # Routing Grid Definitions
    for sc_name, pdk_name in [('m1', 'M1')]:
        chip.set('pdk','aprlayer', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','aprlayer', stackup, sc_name, 'hoffset', '0.036')
        chip.set('pdk','aprlayer', stackup, sc_name, 'hgrid',  '0.036')
        chip.set('pdk','aprlayer', stackup, sc_name, 'voffset', '0.036')
        chip.set('pdk','aprlayer', stackup, sc_name, 'vgrid',  '0.036')

    for sc_name, pdk_name in [('m2', 'M2')]:
        chip.set('pdk','aprlayer', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','aprlayer', stackup, sc_name, 'hoffset', '0.018')
        chip.set('pdk','aprlayer', stackup, sc_name, 'hgrid',  '0.036')
        chip.set('pdk','aprlayer', stackup, sc_name, 'voffset', '0.00')
        chip.set('pdk','aprlayer', stackup, sc_name, 'vgrid',  '0.027')

    for sc_name, pdk_name in [('m3', 'M3')]:
        chip.set('pdk','aprlayer', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','aprlayer', stackup, sc_name, 'hoffset', '0.018')
        chip.set('pdk','aprlayer', stackup, sc_name, 'hgrid',  '0.036')
        chip.set('pdk','aprlayer', stackup, sc_name, 'voffset', '0.018')
        chip.set('pdk','aprlayer', stackup, sc_name, 'vgrid',  '0.036')

    for sc_name, pdk_name in [('m4', 'M4')]:
        chip.set('pdk','aprlayer', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','aprlayer', stackup, sc_name, 'hoffset', '0.028')
        chip.set('pdk','aprlayer', stackup, sc_name, 'hgrid',  '0.036')
        chip.set('pdk','aprlayer', stackup, sc_name, 'voffset', '0.069')
        chip.set('pdk','aprlayer', stackup, sc_name, 'vgrid',  '0.048')

    for sc_name, pdk_name in [('m5', 'M5')]:
        chip.set('pdk','aprlayer', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','aprlayer', stackup, sc_name, 'hoffset', '0.040')
        chip.set('pdk','aprlayer', stackup, sc_name, 'hgrid',  '0.048')
        chip.set('pdk','aprlayer', stackup, sc_name, 'voffset', '0.069')
        chip.set('pdk','aprlayer', stackup, sc_name, 'vgrid',  '0.048')

    for sc_name, pdk_name in [('m6', 'M6')]:
        chip.set('pdk','aprlayer', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','aprlayer', stackup, sc_name, 'hoffset', '0.030')
        chip.set('pdk','aprlayer', stackup, sc_name, 'hgrid',  '0.048')
        chip.set('pdk','aprlayer', stackup, sc_name, 'voffset', '0.082')
        chip.set('pdk','aprlayer', stackup, sc_name, 'vgrid',  '0.064')

    for sc_name, pdk_name in [('m7', 'M7')]:
        chip.set('pdk','aprlayer', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','aprlayer', stackup, sc_name, 'hoffset', '0.082')
        chip.set('pdk','aprlayer', stackup, sc_name, 'hgrid',  '0.064')
        chip.set('pdk','aprlayer', stackup, sc_name, 'voffset', '0.036')
        chip.set('pdk','aprlayer', stackup, sc_name, 'vgrid',  '0.064')

    for sc_name, pdk_name in [('m8', 'M8'), ('m9', 'M9')]:
        chip.set('pdk','aprlayer', stackup, sc_name, 'name', pdk_name)
        chip.set('pdk','aprlayer', stackup, sc_name, 'hoffset', '0.098')
        chip.set('pdk','aprlayer', stackup, sc_name, 'hgrid',  '0.08')
        chip.set('pdk','aprlayer', stackup, sc_name, 'voffset', '0.098')
        chip.set('pdk','aprlayer', stackup, sc_name, 'vgrid',  '0.08')

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
             libdir+'/lef/NangateOpenCellLibrary.macro.lef')    
    # gds
    chip.set('stdcell',libname,'gds',
             libdir+'/gds/NangateOpenCellLibrary.gds')
    # site name
    chip.set('stdcell',libname,'site', 'asap7sc7p5t')

    # lib arch
    chip.set('stdcell',libname,'libtype',libtype)

    # lib site/tile/size
    chip.set('stdcell',libname,'width', libwidth)
    chip.set('stdcell',libname,'height', libheight)

    #driver
    chip.add('stdcell',libname,'driver', "BUFx2_ASAP7_75t_R")
    
    # clock buffers
    chip.add('stdcell',libname,'cells','clkbuf', "BUFx2_ASAP7_75t_R")

    # tie cells
    chip.add('stdcell',libname,'cells','tie', ["TIEHIx1_ASAP7_75t_R H",
                                               "TIELOx1_ASAP7_75t_R L"])


    # hold cells
    chip.add('stdcell',libname,'cells','hold', "BUFx2_ASAP7_75t_R")

    # filler
    chip.add('stdcell',libname,'cells','filler', ["FILLER_ASAP7_75t_R"]
    
    # Stupid small cells
    chip.add('stdcell',libname,'cells','ignore', ["*x1_ASAP7*",
                                                  "*x1p*_ASAP7*",
                                                  "*xp*_ASAP7*",
                                                  "SDF*",
                                                  "ICG*",
                                                  "DFFH*"]
             
    # Tapcell
    chip.add('stdcell',libname,'cells','tapcell', "FILLCELL_X1")

    # Endcap
    chip.add('stdcell',libname,'cells','endcap', "FILLCELL_X1")

        
#########################
def setup_design(chip):

    chip.set('asic', 'stackup', chip.get('pdk', 'stackup')[0])
    chip.set('asic', 'targetlib', chip.getkeys('stdcell'))
    chip.set('asic', 'minlayer', "m2")
    chip.set('asic', 'maxlayer', "m7")
    chip.set('asic', 'maxfanout', "64")
    chip.set('asic', 'maxlength', "1000")
    chip.set('asic', 'maxslew', "1.5e-9")
    chip.set('asic', 'maxcap', "1e-12")
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
