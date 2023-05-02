import siliconcompiler

import pytest

from siliconcompiler.tools.builtin import join


@pytest.mark.quick
def test_builtin():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    chip.node(flow, 'A', join)

    assert chip.get('flowgraph', flow, 'A', '0', 'tool') == "builtin"
    assert chip.get('flowgraph', flow, 'A', '0', 'task') == "join"


@pytest.mark.quick
def test_import_task():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    from siliconcompiler.tools.yosys import syn_asic
    chip.node(flow, 'A', syn_asic)

    assert chip.get('flowgraph', flow, 'A', '0', 'tool') == "yosys"
    assert chip.get('flowgraph', flow, 'A', '0', 'task') == "syn_asic"
    assert chip.get('flowgraph', flow, 'A', '0', 'taskmodule') == "siliconcompiler.tools.yosys.syn_asic"


@pytest.mark.quick
def test_string_task():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    chip.node(flow, 'A', 'siliconcompiler.tools.yosys.syn_asic')

    assert chip.get('flowgraph', flow, 'A', '0', 'tool') == "yosys"
    assert chip.get('flowgraph', flow, 'A', '0', 'task') == "syn_asic"
    assert chip.get('flowgraph', flow, 'A', '0', 'taskmodule') == "siliconcompiler.tools.yosys.syn_asic"
