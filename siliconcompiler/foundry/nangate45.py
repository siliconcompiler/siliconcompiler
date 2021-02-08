
import os
import sys
import re
import siliconcompiler as sc

####################################################
# PDK Setup
####################################################

def nangate45_pdk(chip, root):

    foundry = 'virtual'
    process = 'nangate45'
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
    chip.add('sc_pdk_foundry', foundry)
    chip.add('sc_pdk_process', process)
    chip.add('sc_pdk_version', version)
    chip.add('sc_pdk_stackup', stackup)
   
    # DRC
    chip.add('sc_tool','drc','script',pdkdir+'/drc/FreePDK45.lydrc')

    # hard coded target lib
    chip.add('sc_target_stackup',chip.get('sc_pdk_stackup')[0])

    # PNR tech file
    chip.add('sc_pdk_pnrtech',stackup, libarch, vendor,
               pdkdir+'/pnr/nangate45.tech.lef')

    # Techlef Overrides
    chip.add('sc_pdk_pnrlayer',stackup, 'metal1 X 0.095 0.19')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal1 Y 0.07  0.14')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal2 X 0.095 0.19')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal2 Y 0.07  0.14')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal3 X 0.095 0.19')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal3 Y 0.07  0.14')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal4 X 0.095 0.28')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal4 Y 0.07  0.28')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal5 X 0.095 0.28')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal5 Y 0.07  0.28')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal6 X 0.095 0.28')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal6 Y 0.07  0.28')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal7 X 0.095 0.8')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal7 Y 0.07  0.8')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal8 X 0.095 0.8')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal8 Y 0.07  0.8')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal9 X 0.095 1.6')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal9 Y 0.07  1.6')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal10 X 0.095 1.6')
    chip.add('sc_pdk_pnrlayer',stackup, 'metal10 Y 0.07 1.6')
    
####################################################
# Library Setup
####################################################
def nangate45_lib(chip, root):

    foundry = 'virtual'
    process = 'nangate45'
    libname = 'NangateOpenCellLibrary'
    libarch = '10t'
    version = 'r1p0'
    corner = 'typical'
    objectives = ['setup','hold']
    libdir = '/'.join([root,
                       foundry,
                       process,
                       'library',
                       libname,
                       version])

    # version
    chip.add('sc_stdcells',libname,'version',version)
    
    # timing
    chip.add('sc_stdcells',libname,'nldm','typical',libdir+'/lib/NangateOpenCellLibrary_typical.lib')
    
    # lef
    chip.add('sc_stdcells',libname,'lef',libdir+'/lef/NangateOpenCellLibrary.macro.lef')
    
    # gds
    chip.add('sc_stdcells',libname,'gds',libdir+'/gds/NangateOpenCellLibrary.gds')

    # site name
    chip.add('sc_stdcells',libname,'site','FreePDK45_38x28_10R_NP_162NW_34O')
    
    # hard coded target lib
    chip.add('sc_target_lib',libname)
    chip.add('sc_target_libarch',libarch)

    # hard coded mcmm settings
    chip.add('sc_mcmm_libcorner',corner)
    chip.add('sc_mcmm_pexcorner',corner)
    chip.add('sc_mcmm_scenario','nominal','libcorner', corner)
    chip.add('sc_mcmm_scenario','nominal','pexcorner', corner)
    chip.add('sc_mcmm_scenario','nominal','opcond', corner+" "+libname)
    chip.add('sc_mcmm_scenario','nominal','objectives', objectives)

    #defaukt floor-planning settings
    chip.add('sc_density', '30')
    chip.add('sc_coremargin', '1.0')
    chip.add('sc_aspectratio', '1')
    
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
    nangate45_pdk(chip, datadir)
    nangate45_lib(chip, datadir)    
    # write out result
    chip.writecfg(output)

   
