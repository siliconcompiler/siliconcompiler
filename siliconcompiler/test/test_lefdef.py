# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import unittest

from pathlib import Path
from siliconcompiler.leflib import *
from siliconcompiler.deflib import *

# TODO: test that parsing results are correct

class TestLefDef(unittest.TestCase):

    def test_lef(self):
        lefdata = Path('asic/virtual/freepdk45/pdk/r1p0/apr/freepdk45.tech.lef').read_text()
        mylef = Lef()
        lef = mylef.parse(lefdata)

    def test_def(self):
        defdata = Path('siliconcompiler/test/complete.5.8.def').read_text()
        mydef = Def()
        mydef.parse(defdata)
