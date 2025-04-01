#!/usr/bin/env python3

import siliconcompiler
from yosys import syn
from openroad import apr
from lambdapdk import sky130
from lambdapdk.sky130.libs import sky130sc

####################################################
# Design Setup
####################################################

chip = siliconcompiler.Chip('heartbeat')
chip.use(sky130)
chip.use(sky130sc)
chip.input("heartbeat.v")
chip.input("heartbeat.sdc")
chip.set('option', 'flow', 'myflow')
chip.set('option', 'pdk', 'skywater130')
chip.set('option', 'stackup', '5M1LI')
chip.set('asic', 'logiclib', 'sky130hd')
chip.set('asic', 'delaymodel', 'nldm')

####################################################
# Flow Setup
####################################################

chip.node('myflow', 'syn', syn)
chip.node('myflow', 'apr', apr)
chip.edge('myflow', 'syn', 'apr')

####################################################
# Run
####################################################

chip.run()

####################################################
# Get Metrics
####################################################
