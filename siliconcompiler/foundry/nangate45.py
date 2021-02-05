
import os
import siliconcompiler as sc

####################################################
# PDK Setup
####################################################

def setup_nangate45_pdk(chip):

    process = 'nangate45'
    version = 'r1p0'
    stackup = '10M'
    vendor = 'openroad'
    lib = '10t'
    pdkdir = ""

    # process name
    chip.add('sc_pdk_foundry', 'virtual')
    chip.add('sc_pdk_process', process)
    chip.add('sc_pdk_version', version)
    chip.add('sc_pdk_stackup', stackup)
    
    # PNR tech file
    chip.add('sc_pdk_pnrtech',stackup,lib,vendor,
               pdkdir+'/pnr/nangate45.tech.lef')
    
    # DRC
    chip.add('sc_tool','drc','script',pdkdir+'/drc/FreePDK45.lydrc')

####################################################
# Library Setup
####################################################
def setup_nangate45_library(chip):
    library = 'NangateOpenCellLibrary'
    version = 'r1p0'
    ipdir = ""
    
    # version
    chip.add('sc_stdcells',library,'version',version)
    
    # timing
    chip.add('sc_stdcells',library,'nldm','typical',ipdir+'/lib/NangateOpenCellLibrary_typical.lib')
    
    # lef
    chip.add('sc_stdcells',library,'lef',ipdir+'/lef/NangateOpenCellLibrary.macro.lef')
    
    # gds
    chip.add('sc_stdcells',library,'gds',ipdir+'/gds/NangateOpenCellLibrary.gds')


#########################
if __name__ == "__main__":    

    # files
    fileroot = os.path.splitext(os.path.abspath(__file__))[0]
    jsonfile = fileroot + '.json'
    # create a chip instance
    chip = sc.Chip()
    # load configuration
    setup_nangate45_pdk(chip)
    setup_nangate45_library(chip)    
    # write out storage file
    chip.writecfg(jsonfile)
