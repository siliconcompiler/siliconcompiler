
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
    version = 'r1p0'
    stackup = '10M'
    vendor = 'openroad'
    libarch = '10t'
    pdkdir = '/'.join([root,
                       foundry,
                       process,
                       'pdk',
                       version])

    # process name
    chip.add('pdk_foundry', foundry)
    chip.add('pdk_process', process)
    chip.add('pdk_version', version)
    chip.add('pdk_stackup', stackup)
   
    # DRC
    chip.add('tool','drc','script',pdkdir+'runsets/klayout/freepdk45.lydrc')

    # DISPLAY
    chip.add('tool','gdsview','script',pdkdir+'setup/klayout/freepdk45.lyt')

    # hard coded target lib
    chip.add('target_stackup',chip.get('pdk_stackup')[0])

    # APR tech file
    chip.add('pdk_aprtech',stackup, libarch, vendor,
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
    libarch = '10t'
    height = '1.4'
    version = 'r1p0'
    corner = 'typical'
    objectives = ['setup']
    libdir = '/'.join([root,
                       foundry,
                       process,
                       'libraries',
                       libname,
                       version])


    # hard coded target lib
    chip.add('target_lib',libname)
    chip.add('target_libarch',libarch)

    #############################################
    # Library Definition
    #############################################
    
    # version
    chip.add('stdcells',libname,'version',version)
    
    # timing
    chip.add('stdcells',libname,'nldm','typical',libdir+'/lib/NangateOpenCellLibrary_typical.lib')
    
    # lef
    chip.add('stdcells',libname,'lef',libdir+'/lef/NangateOpenCellLibrary.macro.lef')
    
    # gds
    chip.add('stdcells',libname,'gds',libdir+'/gds/NangateOpenCellLibrary.gds')

    # site name
    chip.add('stdcells',libname,'site','FreePDK45_38x28_10R_NP_162NW_34O')

    # lib arch
    chip.add('stdcells',libname,'libarch',libarch)

    # lib height
    chip.add('stdcells',libname,'height',height)
    

    #############################################
    # MMCM Flow
    #############################################

    # hard coded mcmm settings
    chip.add('mcmm_cornerlist',corner)
    chip.add('mcmm_pexlist',corner)
    chip.add('mcmm_scenario','nominal','libcorner', corner)
    chip.add('mcmm_scenario','nominal','pexcorner', corner)
    chip.add('mcmm_goals','nominal','syn',  'setup')
    chip.add('mcmm_goals','nominal','place', 'setup')
    all_goals = ['setup', 'hold']
    for stage in ('cts','route','signoff'):
        chip.add('mcmm_goals','nominal', stage, all_goals)
    
    
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

   
