# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler as sc

# Create instance of Chip class
chip = sc.Chip()

# Print defult values
chip.writejson("default.json")

# Demostrating use of general python variables (your names)

design = 'hello_world'
source = 'example/hello_world.v'
floorplan = 'example/hello_world.def'
sdc = 'example/hello_world.sdc'
foundry = 'acme'
process  = '22nm'
stdlib  = 'mylib.lib'
nominal_corner = "tt 1.0 25  all all"
hold_corner    = "ff 1.1 125 hold all"
setup_corner   = "ss 0.9 125 setup all"
leakage_corner = "ff 1.1 125  leakage signoff"

# Inserting value into configuration
chip.set('sc_design', design)
chip.set('sc_source', source)
chip.set('sc_def', floorplan)
chip.set('sc_constraints', sdc)
chip.set('sc_foundry', foundry)
chip.set('sc_process', process)
chip.set('sc_lib', stdlib)
chip.set('sc_scenario', nominal_corner)
chip.add('sc_scenario', hold_corner)
chip.add('sc_scenario', setup_corner)
chip.add('sc_scenario', leakage_corner)

# Print out new merged config to a file
chip.writejson("new.json") 

# Print out only the non-default values
chip.writejson("diff.json", mode="diff")
