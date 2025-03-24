# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler
import pytest

from siliconcompiler.tools.icarus import compile

from siliconcompiler.tools.builtin import nop
from siliconcompiler.targets import freepdk45_demo


@pytest.mark.eda
@pytest.mark.quick
def test_icarus():
    ydir = os.path.join('stdlib', 'hdl')

    design = "oh_fifo_sync"
    topfile = os.path.join(ydir, f'{design}.v')

    chip = siliconcompiler.Chip(design)

    chip.register_source('oh',
                         'git+https://github.com/aolofsson/oh',
                         '23b26c4a938d4885a2a340967ae9f63c3c7a3527')

    chip.use(freepdk45_demo)
    chip.set('option', 'ydir', ydir, package='oh')
    chip.input(topfile, package='oh')

    flow = 'sim'
    chip.node(flow, 'import', nop)
    chip.node(flow, 'compile', compile)
    chip.edge(flow, 'import', 'compile')
    chip.set('option', 'flow', flow)

    assert chip.run()

    # check that compilation succeeded
    assert chip.find_result('vvp', step='compile') is not None
