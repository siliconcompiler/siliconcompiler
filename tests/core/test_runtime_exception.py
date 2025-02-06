# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import pytest

import siliconcompiler
from siliconcompiler.targets import asic_demo
from siliconcompiler.targets import asap7_demo


def test_version():
    chip = siliconcompiler.Chip('test')

    chip.use(asic_demo)

    flow = chip.get('option', 'flow')
    chip.set('flowgraph', flow, 'import', '0', 'tool', 'dummy')
    chip.set('flowgraph', flow, 'import', '0', 'taskmodule', 'tests.core.tools.dummy.import')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        chip.run(raise_exception=True)


def test_run_fails():
    chip = siliconcompiler.Chip("test")
    chip.use(asap7_demo)
    chip.set('option', 'to', 'syn')
    assert chip.run() is False


def test_run_fails_with_exception():
    chip = siliconcompiler.Chip("test")
    chip.use(asap7_demo)
    chip.set('option', 'to', 'syn')
    with pytest.raises(siliconcompiler.SiliconCompilerError):
        chip.run(raise_exception=True)
