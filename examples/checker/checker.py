# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler
import os
import re

# Create instance of Chip class
chip = siliconcompiler.Chip(loglevel='INFO')

#legal values
chip.set('quiet','true')
chip.set('jobid','4')
chip.set('idir','/dev')
chip.set('source','/bin/sh')

#illegal
chip.set('quiet',' true')
chip.set('jobid','wrong!')
chip.set('idir','/bin/sh')
chip.set('source','what?*')

