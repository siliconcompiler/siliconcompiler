
import os
import sys
import re
import siliconcompiler

####################################################
# Library Setup
####################################################
def setup_libs(chip):

    foundry = 'virtual'
    process = 'freepdk45'
    libname = 'NangateOpenCellLibrary'
    libtype = '10t'
    size = '0.19 1.4'
    rev = 'r1p0'
    corner = 'typical'
    objectives = ['setup']
    libdir = '/'.join(["foundry",
                       foundry,
                       process,
                       'libs',
                       libname,
                       rev])

    # rev
    chip.add('stdcells',libname,'rev',rev)    

    # timing
    chip.add('stdcells',libname, 'model', 'typical', 'nldm', 'lib',
             libdir+'/lib/NangateOpenCellLibrary_typical.lib')
    
    # lef
    chip.add('stdcells',libname,'lef',
             libdir+'/lef/NangateOpenCellLibrary.macro.lef')    
    # gds
    chip.add('stdcells',libname,'gds',
             libdir+'/gds/NangateOpenCellLibrary.gds')
    # site name
    chip.add('stdcells',libname,'site',
             'FreePDK45_38x28_10R_NP_162NW_34O')
    # lib arch
    chip.add('stdcells',libname,'libtype',libtype)

    # lib site/tile/size
    chip.add('stdcells',libname,'size',size)
    
    # hard coded mcmm settings
    chip.add('mcmm','worst','libcorner', corner)
    chip.add('mcmm','worst','pexcorner', corner)
    chip.add('mcmm','worst','mode', 'func')
    chip.add('mcmm','worst','check', ['setup','hold'])
    
    # hard coded target lib
    chip.add('target_lib',libname)

#########################
if __name__ == "__main__":    

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_libs(chip)
    # write out result
    chip.writecfg(output)

   
