# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import re
import os
import siliconcompiler

#Create one (or many...) instances of Chip class
chip = siliconcompiler.Chip(loglevel="INFO")

#Printing fetch keylists
#If no arg supplied, fetch all keys
print(chip.getkeys('asic'))
allkeys = chip.getkeys()
for key in allkeys:
    print(key)





