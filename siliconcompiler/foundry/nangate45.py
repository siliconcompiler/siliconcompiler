
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
    lib = '10t'
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
    
    # PNR tech file
    chip.add('sc_pdk_pnrtech',stackup, lib, vendor,
               pdkdir+'/pnr/nangate45.tech.lef')

    # DRC
    chip.add('sc_tool','drc','script',pdkdir+'/drc/FreePDK45.lydrc')

####################################################
# Library Setup
####################################################
def nangate45_lib(chip, root):

    foundry = 'virtual'
    process = 'nangate45'
    libname = 'NangateOpenCellLibrary'
    version = 'r1p0'
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

   
