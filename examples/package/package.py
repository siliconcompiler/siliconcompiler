# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler
import asyncio
import os

# Create instance of Chip class
chip = siliconcompiler.Chip(loglevel='INFO')

# Inserting value into configuration
chip.add('source', 'examples/gcd/gcd.v')
chip.add('design', 'gcd')
chip.add('clock', 'clock_name', 'pin', 'clk')
chip.add('constraint', "examples/gcd/constraint.sdc")
chip.set('target', "freepdk45_asic")
chip.set('asic', 'diesize', "0 0 100.13 100.8")
chip.set('asic', 'coresize', "10.07 11.2 90.25 91")

chip.target()

chip.writecfg('tmp.json')

#default
chip.package(dir='output')

#copy pdk
chip.set('copyall','true')
chip.package(dir='output2')
