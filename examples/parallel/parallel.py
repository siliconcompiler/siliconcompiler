# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler

# Create instance of Chip class
chip = siliconcompiler.Chip(loglevel='INFO')

# PDK
chip.set('target', 'freepdk45')
chip.target()

# Design Specific
chip.add('source', 'examples/parallel/gcd.v')
chip.set('design', 'gcd')
chip.set('asic', 'diesize', '0 0 100.13 100.8')
chip.set('asic', 'coresize', '10.07 11.2 90.25 91')

# Run options
chip.set('quiet', 'true')
chip.set('stop', 'place')

# Compile options
steps = chip.get('steps')
for i in range(5):
    #Modidfy somethhing
    chip.run(jobid=i)
    #measure something
    area = chip.get('real', steps[-1], i, 'area')
    if area == 0:
        break

#Get summary
#should do max here..
chip.summary()


