# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import re
import os
import siliconcompiler

#Create one (or many...) instances of Chip class
chip = siliconcompiler.Chip(loglevel="INFO")

# Reading in default config files unless cfg file is set
chip.help('design')

# Print all help
allkeys = chip.getkeys()
for key in allkeys:
    chip.help(*key)



