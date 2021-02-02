####################################################
# BOILER PLATE
####################################################
import os
import siliconcompiler as sc

mychip = sc.Chip()
scriptdir = os.path.dirname(os.path.realpath(__file__))
#mychip.writecfg("default.json")

####################################################
# Setup
####################################################

library = 'NangateOpenCellLibrary'
version = 'r1p0'
ipdir = scriptdir + '/' + library + '/' + version
outputfile = scriptdir + '/' + library + '.json'

#target lib
mychip.add('sc_target_lib', library)

# timing
mychip.add('sc_stdcell', library, 'nldm', 'typical', ipdir+'/lib/NangateOpenCellLibrary_typical.lib')

# lef
mychip.add('sc_stdcell', library, 'lef', ipdir+'/lef/NangateOpenCellLibrary.macro.lef')

# gds
mychip.add('sc_stdcell', library, 'gds', ipdir+'/gds/NangateOpenCellLibrary.gds')

########################################################
# Write JSON
########################################################

mychip.abspath()

mychip.writecfg(outputfile)
           
