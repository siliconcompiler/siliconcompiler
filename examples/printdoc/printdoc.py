# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import re
import os
import siliconcompiler as sc


#Create one (or many...) instances of Chip class
mychip = sc.Chip()

# Reading in default config files unless cfg file is set
mychip.writecfg("docs/sc_refcard.md", prune=False)


