# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

from siliconcompiler.tools.openroad import openroad
from siliconcompiler.tools.klayout import klayout
from siliconcompiler.tools._common import get_tool_tasks


def test_tool_tasks_openroad():
    chip = siliconcompiler.Chip('test')
    assert get_tool_tasks(chip, openroad) == ['cts',
                                              'dfm',
                                              'export',
                                              'floorplan',
                                              'metrics',
                                              'physyn',
                                              'place',
                                              'rcx_bench',
                                              'rcx_extract',
                                              'rdlroute',
                                              'route',
                                              'screenshot',
                                              'show']


def test_tool_tasks_klayout():
    chip = siliconcompiler.Chip('test')
    assert get_tool_tasks(chip, klayout) == ['convert_drc_db',
                                             'drc',
                                             'export',
                                             'operations',
                                             'screenshot',
                                             'show']
