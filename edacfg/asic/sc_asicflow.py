
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

edadir = scriptdir
threads = 4
outputfile = scriptdir + "/sc_asicflow.json"

# all tools
all_stages = mychip.get('sc_stages')

for stage in all_stages:
     mychip.add('sc_tool', stage, 'np', threads)
     mychip.add('sc_tool', stage, 'refdir', edadir)
     mychip.add('sc_tool', stage, 'format', 'tcl')
     mychip.add('sc_tool', stage, 'copy', 'no')
     
# import
mychip.add('sc_tool', 'import', 'exe', 'verilator')
mychip.add('sc_tool', 'import', 'opt', '--lint-only --debug')

# syn
mychip.add('sc_tool', 'syn', 'exe', 'yosys')
mychip.add('sc_tool', 'syn', 'opt', '-c')
mychip.add('sc_tool', 'syn', 'vendor', 'yosys')
mychip.add('sc_tool', 'syn', 'script', 'sc_syn.tcl')

# pnr
for stage in ('floorplan', 'place', 'cts', 'route', 'signoff'):
     mychip.add('sc_tool', stage, 'script', 'sc_'+stage+'.tcl')
     mychip.add('sc_tool', stage, 'exe', 'openroad')
     mychip.add('sc_tool', stage, 'vendor', 'openroad')
     mychip.add('sc_tool', stage, 'opt', '-no_init -exit')

# export
mychip.add('sc_tool', 'export', 'exe', 'klayout')


########################################################
# Write JSON
########################################################

mychip.abspath()

mychip.writecfg(outputfile)


           
