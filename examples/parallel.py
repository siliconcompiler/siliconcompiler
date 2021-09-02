# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler
chip = siliconcompiler.Chip(design="oh_add", loglevel='INFO')
chip.add('source', 'third_party/designs/oh/stdlib/hdl/oh_add.v')
chip.target('freepdk45_asicflow')
chip.set('relax', "true")
chip.set('quiet', "true")
chip.set('asic', 'diesize', "0 0 100.13 100.8")
chip.set('asic', 'coresize', "10.07 11.2 90.25 91")
n = 20
for step in ('syn','place','cts','route'):
    chip.set('flowgraph',step,'nproc',n)
chip.run()
