# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import os
import sys
import multiprocessing
import siliconcompiler

# Setting up the experiment
rootdir = (os.path.dirname(os.path.abspath(__file__)) +
           "/../../third_party/designs/oh/")
design = 'oh_add'
library = 'mathlib'
width = 100
height = 100
N = 16

chip = siliconcompiler.Chip(loglevel='INFO')
chip.set('design', design)
chip.add('source', rootdir+'/mathlib/hdl/'+design+'.v')
chip.set('param', 'N', str(N))
chip.set('jobid', '0')
chip.set('relax', True)
chip.set('quiet', True)
chip.set('steplist', ['import', 'syn'])
chip.target("asicflow_freepdk45")

# First run
chip.run()

oldid = int(chip.set('jobid', '0'))
old_manifest = chip.find_output(str(oldid), step, index, 'pkg.json')
old_cfg = chip.read_manifest(old_manifest)

# make sure we are going in the right direction
while true:
    oldid = int(chip.get('jobid')[-1])
    old_manifest = chip.find_output(str(oldid), step, index, 'pkg.json')
    old_cfg = chip.read_manifest(old_manifest)

    newid = oldid + 1;
    chip.append('jobid', str(newid))

    chip.run()

    new_manifest = chip.find_output(str(newid), step, index, 'pkg.json')
    new_cfg = chip.read_manifest(mew_manifest)

    if (chip.get('metric','syn','0','cellarea','real', cfg=new_cfg) >=
        chip.get('metric','syn','0','cellarea','real', cfg=old_cfg)):
        break
