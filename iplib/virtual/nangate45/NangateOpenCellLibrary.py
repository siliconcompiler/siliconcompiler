####################################################
# BOILER PLATE
####################################################
import os
import siliconcompiler as sc

mychip = sc.Chip()
scriptdir = os.path.dirname(os.path.realpath(__file__))


####################################################
# Setup
####################################################

library = 'NangateOpenCellLibrary'
version = 'r1p0'
ipdir = scriptdir + '/' + library + '/' + version
outputfile = scriptdir + '/' + library + '.json'

# timing
mychip.set('sc_stdlib', library, 'timing', 'typical', ipdir+'/lib/NangateOpenCellLibrary_typical.lib')

# lef
mychip.set('sc_stdlib', library, 'lef', ipdir+'/lef/NangateOpenCellLibrary.macro.lef')

# gds
mychip.set('sc_stdlib', library, 'gds', ipdir+'/gds/NangateOpenCellLibrary.gds')

########################################################
# Write JSON
########################################################

mychip.abspath()

mychip.writecfg(outputfile)
           
