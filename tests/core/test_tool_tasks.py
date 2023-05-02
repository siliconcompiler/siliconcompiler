# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

from siliconcompiler.tools.openroad import openroad
from siliconcompiler.tools.klayout import klayout


def test_tool_tasks_openroad():
    chip = siliconcompiler.Chip('test')
    assert chip._get_tool_tasks(openroad) == ['cts', 'dfm', 'export', 'floorplan', 'physyn', 'place', 'route', 'screenshot', 'show']


def test_tool_tasks_klayout():
    chip = siliconcompiler.Chip('test')
    assert chip._get_tool_tasks(klayout) == ['export', 'screenshot', 'show']
