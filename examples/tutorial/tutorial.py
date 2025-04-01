#!/usr/bin/env python3

import siliconcompiler
from yosys import syn
from openroad import apr

####################################################
# Design Setup
####################################################

chip = siliconcompiler.Chip('heartbeat')
chip.input("heartbeat.v")
chip.input("heartbeat.sdc")
chip.set('option', 'flow', 'myflow')

chip.set('option', 'pdk', 'skywater130')
chip.set('option', 'stackup', '5M1LI')
chip.set('asic', 'logiclib', 'sky130hd')

####################################################
# Flow Setup
####################################################

chip.node('myflow', 'syn', syn)
chip.node('myflow', 'apr', apr)
chip.edge('myflow', 'syn', 'apr')

####################################################
# PDK Setup
####################################################

process = 'skywater130'
libname = 'sky130hd'
libtype = 'hd'
stackup = '5M1LI'
techlef = ''
lib_lef = ''
lib_liberty = ''

chip.set('pdk', process, 'version', 'v0_0_2')
chip.set('pdk', process, 'stackup', stackup)

# APR Setup
tool = 'openroad'
chip.set('pdk', process, 'aprtech', tool, stackup, libtype, 'lef', techlef)
chip.set('pdk', process, 'minlayer', stackup, 'met1')
chip.set('pdk', process, 'maxlayer', stackup, 'met5')

# Syn/APR library setup
chip.add('library', libname, 'output', 'fast', 'nldm', lib_liberty)
chip.add('library', libname, 'output', stackup, 'lef', lib_lef)

#dict set sc_cfg "library" "sky130hd" "output" "fast" "nldm" [list "/nfs/sc_compute/cache/lambdapdk-v0.1.43/lambdapdk/sky130/libs/sky130hd/nldm/sky130_fd_sc_hd__ff_100C_1v95.lib.gz"]



####################################################
# Run
####################################################

chip.run()

####################################################
# Get Metrics
####################################################
