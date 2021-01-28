# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler as sc

# Create instance of Chip class
chip = sc.Chip()

# Print defult values
chip.writecfg("default.json")
chip.readcfg(".json")

# Demostrating use of general python variables (your names)

design = 'hello_world'
source = 'example/hello_world.v'
floorplan = 'example/hello_world.def'
sdc = 'example/hello_world.sdc'
foundry = 'acme'
process  = '22nm'
stdlib  = 'mylib.lib'
nominal_corner = "tt 1.0 25  all all"

# Inserting value into configuration
chip.set('sc_design', design)
chip.set('sc_source', source)
chip.set('sc_def', floorplan)
chip.set('sc_constraints', sdc)
chip.set('sc_foundry', foundry)
chip.set('sc_process', process)
chip.set('sc_lib', stdlib)
chip.set('sc_scenario', nominal_corner)

# Print out new merged config to a file
chip.writecfg("new.json") 
