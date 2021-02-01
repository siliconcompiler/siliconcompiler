
####################################################
# BOILER PLATE
####################################################

import os
import siliconcompiler as sc

mychip = sc.Chip()
scriptdir = os.path.dirname(os.path.realpath(__file__))
mychip.writecfg('default.json')

####################################################
# Setup
####################################################

process = 'nangate45'
version = 'r1p0'
stackup = '3MA_3MB_2MC_2MD'
vendor = 'openroad'
lib = '10t'
pdkdir = scriptdir + "/" + version
outputfile = scriptdir + "/" + process + ".json"

# process name
mychip.add('sc_pdk_process', process)

# normalize node (in nm)
mychip.add('sc_pdk_node', '45')

# PNR tech file
mychip.add('sc_pdk_pnrtech', stackup, lib, vendor, pdkdir + '/pnr/nangate45.tech.lef')

# PNR routing layer setup
mychip.add('sc_pdk_pnrlayer', stackup, 'metal1  X 0.095  0.19')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal1  Y 0.070  0.14')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal2  X 0.095  0.19')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal2  Y 0.070  0.14')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal3  X 0.095  0.19')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal3  Y 0.070  0.14')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal4  X 0.095  0.28')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal4  Y 0.070  0.28')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal5  X 0.095  0.28')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal5  Y 0.070  0.28')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal6  X 0.095  0.28')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal6  Y 0.070  0.28')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal7  X 0.095  0.80')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal7  Y 0.070  0.80')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal8  X 0.095  0.80')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal8  Y 0.070  0.80')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal9  X 0.095  1.60')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal9  Y 0.070  1.60')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal10 X 0.095  1.60')
mychip.add('sc_pdk_pnrlayer', stackup, 'metal10 Y 0.070  1.60')

# DRC
mychip.add('sc_tool', 'drc', 'script',  pdkdir + '/drc/FreePDK45.lydrc')

########################################################
# Write JSON
########################################################
mychip.writecfg(outputfile)
mychip.abspath()
mychip.writecfg(outputfile)




           
