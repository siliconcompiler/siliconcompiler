# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler
import random

chip = siliconcompiler.Chip(design='gcd', loglevel='INFO')
chip.target("freepdk45_asicflow")

# Setting up design
chip.add('source', 'examples/gcd/gcd.v')
chip.add('constraint', "examples/gcd/gcd.sdc")
chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
chip.set('asic', 'corearea', [(10.07,11.2), (90.25,91)])

# Options
chip.set('relax', True)
chip.set('quiet', True)

# Making placement parallel
N = 10
chip.clone('place', N)
for i in range(N):
    randval = random.choice(range(N))
    chip.set('eda', 'openroad', 'place', str(i), 'option', 'place_density', str(randval*0.1))

# Runnning the
chip.run()
chip.summary()
