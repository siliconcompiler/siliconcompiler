
import os
import siliconcompiler as sc

mychip = sc.Chip()
scriptdir = os.path.dirname(os.path.realpath(__file__))

##############
# General
##############

process = 'nangate45'
version = 'r1p0'
pdkdir = scriptdir + version

# process name
mychip.set('sc_process', process)

# normalize node (in nm)
mychip.set('sc_node', '45')

# name of metal stack
mychip.set('sc_metalstack', '3MA_3MB_2MC_2MD')

##############
# PNR Setup
##############

# PNR tech file
mychip.set('sc_techfile', pdkdir + 'pnr/nangate45.tech.lef')

# PNR routing layer setup
mychip.set('sc_layer', 'metal1  X 0.095  0.19')
mychip.set('sc_layer', 'metal1  Y 0.070  0.14')
mychip.set('sc_layer', 'metal2  X 0.095  0.19')
mychip.set('sc_layer', 'metal2  Y 0.070  0.14')
mychip.set('sc_layer', 'metal3  X 0.095  0.19')
mychip.set('sc_layer', 'metal3  Y 0.070  0.14')
mychip.set('sc_layer', 'metal4  X 0.095  0.28')
mychip.set('sc_layer', 'metal4  Y 0.070  0.28')
mychip.set('sc_layer', 'metal5  X 0.095  0.28')
mychip.set('sc_layer', 'metal5  Y 0.070  0.28')
mychip.set('sc_layer', 'metal6  X 0.095  0.28')
mychip.set('sc_layer', 'metal6  Y 0.070  0.28')
mychip.set('sc_layer', 'metal7  X 0.095  0.80')
mychip.set('sc_layer', 'metal7  Y 0.070  0.80')
mychip.set('sc_layer', 'metal8  X 0.095  0.80')
mychip.set('sc_layer', 'metal8  Y 0.070  0.80')
mychip.set('sc_layer', 'metal9  X 0.095  1.60')
mychip.set('sc_layer', 'metal9  Y 0.070  1.60')
mychip.set('sc_layer', 'metal10 X 0.095  1.60')
mychip.set('sc_layer', 'metal10 Y 0.070  1.60')

##############
# DRC
##############

mychip.set('sc_tool', 'drc', 'script',  pdkdir + 'drc/FreePDK45.lydrc')

##############
# Write Out CFG
##############
mychip.abspath()
mychip.writecfg(pdkdir + "/" + process + ".json")
           
