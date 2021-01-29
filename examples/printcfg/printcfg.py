# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import re
import os
import siliconcompiler as sc

scriptdir = os.path.dirname(os.path.abspath(__file__))
rootdir = re.sub("examples/printcfg", "", scriptdir, 1)
pdkcfg = rootdir + "/pdklib/virtual/nangate45/nangate45.json"
ipcfg = rootdir + "/iplib/virtual/nangate45/NangateOpenCellLibrary.json"
edacfg = rootdir + "/edalib/asic/sc_asicflow.json"


#Create one (or many...) instances of Chip class
mychip = sc.Chip()

# Reading in default config files unless cfg file is set
mychip.readcfg(edacfg)
mychip.readcfg(pdkcfg)
mychip.readcfg(ipcfg)

mychip.printcfg(mychip.cfg, prefix="dict set cfg")

