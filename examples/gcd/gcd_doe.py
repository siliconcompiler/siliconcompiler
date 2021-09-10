# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler
chip = siliconcompiler.Chip(loglevel='INFO')
chip.target("freepdk45_asicflow")
chip.add('source', 'examples/gcd/gcd.v')
chip.set('design', 'gcd')
chip.set('relax', True)
chip.set('quiet', True)
chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
chip.set('asic', 'corearea', [(10.07,11.2),(90.25,91)])

N = 10
chip.set('flowgraph','place','nproc',N)
for index in range(N):
    chip.set('eda', 'openroad', 'place', str(index),
             'option', 'place_density', str(index*0.1))
    print(index)
chip.run()
chip.summary()
