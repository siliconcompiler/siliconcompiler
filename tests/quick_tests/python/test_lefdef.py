# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import unittest

from pathlib import Path
import os
from siliconcompiler.leflib import *
from siliconcompiler.deflib import *

# TODO: test that parsing results are correct

class TestLefDef(unittest.TestCase):

    def test_lef(self):
        mydir = os.path.dirname(os.path.abspath(__file__))
        sc_root = f'{mydir}/../../..'
        lefdata = Path(f'{sc_root}/third_party/foundry/virtual/freepdk45/pdk/r1p0/apr/freepdk45.tech.lef').read_text()
        mylef = Lef()
        lef = mylef.parse(lefdata)

    def test_def(self):
        mydir = os.path.dirname(os.path.abspath(__file__))
        sc_root = f'{mydir}/../../..'
        defdata = Path(f'{sc_root}/tests/quick_tests/python/complete.5.8.def').read_text()
        mydef = Def()
        mydef.parse(defdata)
