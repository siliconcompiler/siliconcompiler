# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
#
# This example shows how one could map from legacy names to
# the siliconcompiler names. The example specifically
# translates from the openroad make format.
# https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts

import siliconcompiler as sc

# Create instance of Chip class
chip = sc.Chip()
chip.writecfg("default.json")

# Timing
chip.set('sc_stdlib', 'lib1', 'timing', 'tt', "lib1_tt.lib")
chip.set('sc_stdlib', 'lib1', 'timing', 'ff', "lib1_ff.lib")
chip.set('sc_stdlib', 'lib1', 'timing', 'ss', "lib1_ss.lib")
chip.set('sc_stdlib', 'lib2', 'timing', 'tt', "lib2_tt.lib")
chip.set('sc_stdlib', 'lib2', 'timing', 'ff', "lib2_ff.lib")
chip.set('sc_stdlib', 'lib2', 'timing', 'ss', "lib2_ss.lib")

#Lefs
chip.set('sc_stdlib', 'lib1', 'lef', "lib1.lef")
chip.set('sc_stdlib', 'lib2', 'lef', "lib2.lef")

# Print out mapped tcl
chip.writecfg("slice.json")
print(chip.slice('sc_stdlib', 'tt'))
print(chip.slice('sc_stdlib', 'lef'))
