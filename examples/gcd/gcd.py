# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler
chip = siliconcompiler.Chip()
chip.add('source', 'examples/gcd/gcd.v')
chip.add('design', 'gcd')
chip.add('constraint', "examples/gcd/gcd.sdc")
chip.set('asic', 'diesize', "0 0 100.13 100.8")
chip.set('asic', 'coresize', "10.07 11.2 90.25 91")
chip.target("freepdk45_asic")
chip.run()
chip.summary() 
