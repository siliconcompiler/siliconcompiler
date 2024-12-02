# Copyright 2023 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler

from siliconcompiler.tools import openroad
from siliconcompiler.tools.klayout import klayout
from siliconcompiler.tools._common import get_tool_tasks


def test_tool_tasks_openroad():
    chip = siliconcompiler.Chip('test')
    assert get_tool_tasks(chip, openroad) == [
        'antenna_repair',
        'clock_tree_synthesis',
        'detailed_placement',
        'detailed_route',
        'endcap_tapcell_insertion',
        'fillercell_insertion',
        'fillmetal_insertion',
        'global_placement',
        'global_route',
        'init_floorplan',
        'macro_placement',
        'metrics',
        'pin_placement',
        'power_grid',
        'rcx_bench',
        'rcx_extract',
        'rdlroute',
        'repair_design',
        'repair_timing',
        'screenshot',
        'show',
        'write_data'
    ]


def test_tool_tasks_klayout():
    chip = siliconcompiler.Chip('test')
    assert get_tool_tasks(chip, klayout) == ['convert_drc_db',
                                             'drc',
                                             'export',
                                             'operations',
                                             'screenshot',
                                             'show']
