import os

import pytest

import siliconcompiler
from siliconcompiler.tools.surelog import parse
from siliconcompiler.tools.verilator import lint


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.parametrize('task', [parse, lint])
def test_libext(task, datadir):
    chip = siliconcompiler.Chip('top')

    test_dir = os.path.join(datadir, 'test_libext')
    chip.input(os.path.join(test_dir, 'top.v'))
    chip.set('option', 'ydir', test_dir)
    chip.set('option', 'libext', 'verilog')

    chip.set('option', 'flow', 'test')
    chip.node('test', 'import', task)

    assert chip.run()
