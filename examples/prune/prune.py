# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import json
import siliconcompiler as sc

# Create instance of Chip class
chip = sc.Chip()

# Setting some values

design = 'hello_world'

# Inserting value into configuration
chip.add('design', design)
chip.writecfg('all.json')
chip.writecfg('prune.json')

