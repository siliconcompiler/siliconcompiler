
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

#default = scriptdir + "/sc_default.json"
#mychip.writecfg(default)

# all tools
all_stages = mychip.get('sc_stages')

for stage in all_stages:
     mychip.set('sc_tool', stage, 'np', threads)
     mychip.set('sc_tool', stage, 'refdir', edadir)
     mychip.set('sc_tool', stage, 'format', 'tcl')
     mychip.set('sc_tool', stage, 'copy', 'no')
     mychip.set('sc_tool', stage, 'script', 'sc_'+stage+'.tcl')
     
# import
mychip.set('sc_tool', 'import', 'exe', 'verilator')
mychip.set('sc_tool', 'import', 'opt', '--lint-only --debug')

# syn
mychip.set('sc_tool', 'syn', 'exe', 'yosys')
mychip.set('sc_tool', 'syn', 'opt', '-c')

# pnr
for stage in ('floorplan', 'place', 'cts', 'route', 'signoff'):
    mychip.set('sc_tool', stage, 'exe', 'openroad')
    mychip.set('sc_tool', stage, 'opt', '-no_init -exit')

# export
mychip.set('sc_tool', 'export', 'exe', 'klayout')


########################################################
# Write JSON
########################################################

mychip.abspath()

mychip.writecfg(outputfile)


           
