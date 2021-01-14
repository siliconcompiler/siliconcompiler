# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler as sc

# Create instance of Chip class
chip = sc.Chip()

# Print defult values
chip.writejson("default.json")

# Set a variable in the config structure
chip.set('sc_design', "MY_DESIGN")

# Write out the new config file
chip.writejson("modified.json")

# Compare tehmodified version to the default version
same = chip.compare("default.json", "modified.json")

if not same:
    print("WARNING: the two files are different")
