# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler
import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_ghdl(datadir):
    design = "adder"
    design_src = os.path.join(datadir, f'{design}.vhdl')

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.load_target('freepdk45_demo')
    chip.set('source', design_src)
    chip.set('design', design)
    chip.set('mode', 'sim')

    chip.single_step('import', 'ghdl')
    chip.set('flow', 'ghdl')

    chip.run()

    # check that compilation succeeded
    assert chip.find_result('v', step='import') is not None

#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_ghdl(datadir(__file__))
