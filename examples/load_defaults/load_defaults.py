# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler as sc
import json
import os

path = os.path.dirname(os.path.abspath(__file__))

# Create instance of Chip class
chip = sc.Chip()

# Dump original
chip.writecfg(path+"/init.json")

# Load defaults into active values 
chip.default()

# Load 
chip.writecfg(path+"/default.json")
