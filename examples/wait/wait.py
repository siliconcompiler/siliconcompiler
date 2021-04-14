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
chip.set('status', 'place', 'active','1')

# Run options
chip.set('quiet', 'true')
chip.set('stop', 'place')
chip.run()
chip.wait()
chip.summary()


