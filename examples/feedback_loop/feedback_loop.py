# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import os
import sys
import re
import multiprocessing
import siliconcompiler

# Setting up the experiment
rootdir = (os.path.dirname(os.path.abspath(__file__)) +
           "/../../third_party/designs/oh/")

design = 'oh_add'
library = 'mathlib'
width = 100
height = 100
N = 8

# Pluggin design into SC
chip = siliconcompiler.Chip(loglevel='INFO')
chip.set('design', design)
chip.add('source', rootdir+'/stdlib/hdl/'+design+'.v')
chip.set('param', 'N', str(N))
chip.set('relax', True)
chip.set('quiet', True)
chip.target("asicflow_freepdk45")

# First run
steplist = ['import', 'syn']
chip.set('steplist', steplist)
chip.run()

while True:
    N = N * 2
    # Read in last run
    oldid = chip.get('jobname')[-1]
    old_manifest = chip.find_result('.pkg.json', 'syn', jobname=oldid)
    old_cfg = chip.read_manifest(old_manifest)    

    #Update ID
    match = re.match(r'(.*)(\d+)$', oldid)
    newid = match.group(1) + str(int(match.group(2))+1)
    
    # Running syn only
    chip.add('jobname', newid)
    chip.set('param', 'N', str(N), clobber=True)
    print(chip.get('param', 'N'))
    chip.write_manifest("tmp.json")
    chip.run()

    new_area = chip.get('metric','syn','0','cellarea','real')
    old_area = chip.get('metric','syn','0','cellarea','real', cfg=old_cfg)

    factor = new_area/old_area

    print(N, new_area, old_area, newid, chip.get('jobname'))
    
    # compare result
    if (new_area/old_area) > 2.1:
        print("Stopping, area is exploding")
        break

