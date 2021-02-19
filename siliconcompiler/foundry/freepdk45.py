
import os
import sys
import re
import siliconcompiler as sc

####################################################
# PDK Setup
####################################################

def freepdk45_pdk(chip, root):

    foundry = 'virtual'
    process = 'freepdk45'
    rev = 'r1p0'
    stackup = '10M'
    vendor = 'openroad'
    libtype = '10t'
    pdkdir = '/'.join([root,
                       foundry,
                       process,
                       'pdk',
                       rev])

    # process name
    chip.add('pdk_foundry', foundry)
    chip.add('pdk_process', process)
    chip.add('pdk_rev', rev)
    chip.add('pdk_stackup', stackup)
   
    # DRC
    chip.add('tool','drc','script',pdkdir+'runsets/klayout/freepdk45.lydrc')
    # DISPLAY
    chip.add('tool','gdsview','script',pdkdir+'setup/klayout/freepdk45.lyt')
    # hard coded target lib
    chip.add('stackup',chip.get('pdk_stackup')[0])
    # APR tech file
    chip.add('pdk_aprtech',stackup, libtype, vendor,
               pdkdir+'/apr/freepdk45.tech.lef')

    # Techlef Overrides
    chip.add('pdk_aprlayer',stackup, 'metal1 X 0.095 0.19')
    chip.add('pdk_aprlayer',stackup, 'metal1 Y 0.07  0.14')
    chip.add('pdk_aprlayer',stackup, 'metal2 X 0.095 0.19')
    chip.add('pdk_aprlayer',stackup, 'metal2 Y 0.07  0.14')
    chip.add('pdk_aprlayer',stackup, 'metal3 X 0.095 0.19')
    chip.add('pdk_aprlayer',stackup, 'metal3 Y 0.07  0.14')
    chip.add('pdk_aprlayer',stackup, 'metal4 X 0.095 0.28')
    chip.add('pdk_aprlayer',stackup, 'metal4 Y 0.07  0.28')
    chip.add('pdk_aprlayer',stackup, 'metal5 X 0.095 0.28')
    chip.add('pdk_aprlayer',stackup, 'metal5 Y 0.07  0.28')
    chip.add('pdk_aprlayer',stackup, 'metal6 X 0.095 0.28')
    chip.add('pdk_aprlayer',stackup, 'metal6 Y 0.07  0.28')
    chip.add('pdk_aprlayer',stackup, 'metal7 X 0.095 0.8')
    chip.add('pdk_aprlayer',stackup, 'metal7 Y 0.07  0.8')
    chip.add('pdk_aprlayer',stackup, 'metal8 X 0.095 0.8')
    chip.add('pdk_aprlayer',stackup, 'metal8 Y 0.07  0.8')
    chip.add('pdk_aprlayer',stackup, 'metal9 X 0.095 1.6')
    chip.add('pdk_aprlayer',stackup, 'metal9 Y 0.07  1.6')
    chip.add('pdk_aprlayer',stackup, 'metal10 X 0.095 1.6')
    chip.add('pdk_aprlayer',stackup, 'metal10 Y 0.07 1.6')
    
####################################################
# Library Setup
####################################################
def nangate45_lib(chip, root):

    foundry = 'virtual'
    process = 'freepdk45'
    libname = 'NangateOpenCellLibrary'
    libtype = '10t'
    size = '0.19 1.4'
    rev = 'r1p0'
    corner = 'typical'
    objectives = ['setup']
    libdir = '/'.join([root,
                       foundry,
                       process,
                       'libraries',
                       libname,
                       rev])

    # rev
    chip.add('stdcells',libname,'rev',rev)    
    # timing
    chip.add('stdcells',libname,'nldm','typical','lib',
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
    chip.add('mcmm','worst','goal', ['setup','hold'])
    
    # hard coded target lib
    chip.add('target_lib',libname)

#########################
if __name__ == "__main__":    

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'
    dirname = os.path.dirname(os.path.abspath(__file__))
    datadir = re.sub('siliconcompiler/siliconcompiler','siliconcompiler', dirname)


    # create a chip instance
    chip = sc.Chip()
    # load configuration
    freepdk45_pdk(chip, datadir)
    nangate45_lib(chip, datadir)    
    # write out result
    chip.writecfg(output)

   
