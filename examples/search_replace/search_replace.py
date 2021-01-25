# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler as sc

# Create instance of Chip class
mychip = sc.Chip()

mychip.writecfg("default.json")

# Returning current value
print(mychip.search('sc_effort'))
print(mychip.search('sc_design'))

# Setting value
print(mychip.search('sc_design', ['mydesign'], replace=True))
print(mychip.search('sc_design'))

# Nested query
print(mychip.search('sc_tool', 'import', 'exe'))
print(mychip.search('sc_tool', 'import', 'exe',['verilator'], replace=True))
print(mychip.search('sc_tool', 'import', 'exe'))

print(mychip.search('sc_tool', 'syn', 'exe', ['yosys'], replace=True))
print(mychip.search('sc_tool', 'place', 'exe', ['openroad'], replace=True))

# Write out dictionary to check
mychip.writecfg("update.json")
