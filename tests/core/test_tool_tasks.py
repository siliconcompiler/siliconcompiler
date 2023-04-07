# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

from siliconcompiler.tools.openroad import openroad

def test_tool_tasks():
    chip = siliconcompiler.Chip('test')
    assert chip._get_tool_tasks(openroad) == ['cts', 'dfm', 'export', 'floorplan', 'physyn', 'place', 'route', 'screenshot', 'show']
