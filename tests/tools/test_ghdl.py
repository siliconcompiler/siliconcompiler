# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler
import pytest

from siliconcompiler.tools.ghdl import convert
from siliconcompiler.targets import freepdk45_demo


@pytest.mark.eda
@pytest.mark.quick
def test_ghdl(datadir):
    design = "adder"
    design_src = os.path.join(datadir, f'{design}.vhdl')

    chip = siliconcompiler.Chip(design)
    chip.use(freepdk45_demo)
    chip.input(design_src)

    chip.node('ghdl', 'import', convert)
    chip.set('option', 'flow', 'ghdl')

    chip.run()

    # check that compilation succeeded
    assert chip.find_result('v', step='import') is not None


#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_ghdl(datadir(__file__))
