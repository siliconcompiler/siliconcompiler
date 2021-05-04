# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler
import os
# Create instance of Chip class
chip = siliconcompiler.Chip(loglevel='INFO')

# Inserting value into configuration
chip.set('target', "freepdk45_asic")
chip.target()

chip.set('asic', 'diesize', "0 0 2000 2000")

chip.set('pdk', 'd0', "1")

print("DPW(2x2)",chip.dpw())
print("Net DPW",int(chip.dpw() * chip.calcyield()))

chip.set('asic', 'diesize', "0 0 8000 8000")
print("DPW(8x8)",chip.dpw())
print("Net DPW",int(chip.dpw() * chip.calcyield()))

chip.set('asic', 'diesize', "0 0 16000 16000")
print("DPW(16x16)",chip.dpw())
print("Net DPW",int(chip.dpw() * chip.calcyield()))

chip.set('asic', 'diesize', "0 0 25000 25000")
print("DPW(25x25)",chip.dpw())
print("Net DPW",int(chip.dpw() * chip.calcyield(model='murphy')))
print("Net DPW",int(chip.dpw() * chip.calcyield()))



