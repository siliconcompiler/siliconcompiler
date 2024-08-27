# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import pytest

import siliconcompiler
from siliconcompiler.targets import asic_demo


def test_version():
    chip = siliconcompiler.Chip('test')

    chip.load_target(asic_demo)

    flow = chip.get('option', 'flow')
    chip.set('flowgraph', flow, 'import', '0', 'tool', 'dummy')
    chip.set('flowgraph', flow, 'import', '0', 'taskmodule', 'tests.core.tools.dummy.import')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        chip.run()
