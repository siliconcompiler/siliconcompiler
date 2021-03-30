
import os
import sys
import re
import siliconcompiler

####################################################
# PDK Setup
####################################################

def setup_platform(chip):

    ######################
    # Basic
    ######################

    chip.add('pdk','foundry', 'ERROR')
    chip.add('pdk','process', 'ERROR')
    chip.add('pdk','rev', 'ERROR')
    chip.add('pdk','node', 'ERROR')

    ######################
    # Documentation
    ######################

    chip.add('pdk', 'drm', 'ERROR')
    chip.add('pdk', 'doc', 'ERROR')

    ######################
    # Metal stacks
    ######################

    stackup_list = []
    
    chip.add('pdk', 'stackup', stackup_list)

    #######################
    # Custom Design
    #######################
    
    for stackup in stackup_list:
        chip.add('pdk','display', stackup, 'virtuoso', 'ERROR')
        chip.add('pdk','layermap', stackup, 'gds', 'virtuoso', 'ERROR')
    
    ######################
    # Spice models
    ######################
    
    for stackup in stackup_list:
         chip.add('pdk', 'devicemodels', stackup, 'spice', 'hspice','ERROR')
   
    ######################
    # PEX models
    ######################

    pex_corners = ['ERROR',
                   'ERROR']

    for stackup in stackup_list:
        for corner in pex_corner_list:
            vendor = 'synopsys'
            chip.add('sc_pdk_pexmodels', stackup, corner, vendor, 'ERROR')
            
    ######################
    # APR
    ######################
    
    libtype = ['ERROR',
               'ERROR']

    for stackup in stackup_list:
        for lib in libtype:
            vendor = 'synopsys'
            chip.add('pdk', 'aprtech', stackup, lib, vendor, 'ERROR')
    
            
    #######################
    # Layer Maps
    #######################

    
    
####################################################
# Library Setup
####################################################
def setup_libs(chip, vendor=None):


    liblist = ['ERROR',
               'ERROR']
    
    for lib in liblist:
        
        #libitype
        chip.add('stdcell', lib, 'libtype', 'ERROR')

        #height
        chip.add('stdcell', lib, 'size', 'ERROR')

        #pgmetal
        chip.add('stdcell', lib, 'pgmetal', 'ERROR')

        #user guide
        chip.add('stdcell', lib, 'doc', 'ERROR')

        #datasheet
        chip.add('stdcell', lib, 'datasheet', 'ERROR')

        #lef
        chip.add('stdcell', lib, 'lef', 'ERROR')

        #gds
        chip.add('stdcell', lib, 'gds', 'ERROR')

        #cdl
        chip.add('stdcell', lib, 'cdl', 'ERROR')

        #spice
        chip.add('stdcell', lib, 'spice', 'ERROR')

        #verilog
        chip.add('stdcell', lib, 'hdl', 'ERROR')

        #atpg
        chip.add('stdcell', lib, 'atpg', 'ERROR')

        corners = ['ERROR']
        
        #checks
        for pvt in corners:
            chip.add('stdcell', lib, 'model', pvt, 'check', 'ERROR')

        #models
        for pvt in corners:
            chip.add('stdcell',lib, 'model', pvt, 'nldm', 'bz2', 'ERROR')
                        
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

   
