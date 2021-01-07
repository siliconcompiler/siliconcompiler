# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from pathlib import Path
from leflib import *
from deflib import *

#LEF TEST
lefdata = Path('../third_party/pdklib/virtual/nangate45/r1p0/pnr/nangate45.tech.lef').read_text()

mylef = Lef()

lef = mylef.parse(lefdata)

#DEF TEST

defdata = Path('test/complete.5.8.def').read_text()

mydef = Def()

mydef.parse(defdata)


