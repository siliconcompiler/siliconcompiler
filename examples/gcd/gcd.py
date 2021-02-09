# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler as sc

# Create instance of Chip class
chip = sc.Chip()

# Inserting value into configuration
chip.add('source', 'example/gcd/gcd.v')
chip.add('diesize', "0 0 100.13 100.8")
chip.add('coresize', "10.07 11.2 90.25 91")

chip.writecfg("gcd.json")
