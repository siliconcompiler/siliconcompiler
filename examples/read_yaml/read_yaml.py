# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler as sc

# Create instance of Chip class
chip = sc.Chip()

# Setting some values

design = 'hello_world'
libname = 'mylib'
libarch = '7.5t'
nldmfile = 'mylib.lib.bz2'
corner = 'typical'

# Inserting value into configuration
chip.add('design', design)
chip.add('stdcells', libname,'nldm',corner, 'lib.bz2', nldmfile)
print(chip.get('design'))

# Print out new merged config to a file
chip.writecfg("new.yaml")

#Reading config
chip.readcfg("new.yaml") 
