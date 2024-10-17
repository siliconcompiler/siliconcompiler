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
        'io_pin_placement',
        'macro_placement',
        'power_grid',
        'repair_design',
        'repair_timing',
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
