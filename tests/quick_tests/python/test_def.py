# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import unittest

from pathlib import Path
import os
from siliconcompiler.deflib import *

# TODO: test that parsing results are correct

class TestDef(unittest.TestCase):

    def test_def(self):
        mydir = os.path.dirname(os.path.abspath(__file__))
        sc_root = f'{mydir}/../../..'
        defdata = Path(f'{sc_root}/tests/quick_tests/python/complete.5.8.def').read_text()
        mydef = Def()
        mydef.parse(defdata)
