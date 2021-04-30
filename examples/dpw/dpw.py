# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler
import os
# Create instance of Chip class
chip = siliconcompiler.Chip(loglevel='INFO')

# Inserting value into configuration
chip.set('target', "freepdk45_asic")
chip.target()

chip.set('asic', 'diesize', "0 0 2000 2000")
print("DPW(2x2)",chip.dpw())

chip.set('asic', 'diesize', "0 0 8000 8000")
print("DPW(8x8)",chip.dpw())

chip.set('asic', 'diesize', "0 0 16000 16000")
print("DPW(16x16)",chip.dpw())

chip.set('asic', 'diesize', "0 0 25000 25000")
print("DPW(25x25)",chip.dpw())



