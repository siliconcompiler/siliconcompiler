# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler
import random

chip = siliconcompiler.Chip(design='gcd', loglevel='INFO')

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
val = [1,2,3,4,5,6,7,8,9,10]
chip.set("flowarg", "place_np", str(N))
for i in range(N):
    randval = random.choice(range(N))
    chip.set('eda', 'openroad', 'place', str(i), 'option', 'place_density', str(val[i]*0.1))

chip.target("freepdk45_asicflow")
chip.run()
chip.summary()
