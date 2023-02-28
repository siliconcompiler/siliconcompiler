import siliconcompiler

import pytest

@pytest.mark.quick
def test_builtin():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    chip.node(flow, 'A', siliconcompiler, 'join')

    assert chip.get('flowgraph', flow, 'A', '0', 'tool') == "builtin"

@pytest.mark.quick
def test_string_tool():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    chip.node(flow, 'A', 'siliconcompiler.tools.yosys.yosys', 'syn_asic')

    assert chip.get('flowgraph', flow, 'A', '0', 'tool') == "yosys"
    assert chip.get('flowgraph', flow, 'A', '0', 'toolmodule') == "siliconcompiler.tools.yosys.yosys"
    assert chip.get('flowgraph', flow, 'A', '0', 'task') == "syn_asic"
    assert chip.get('flowgraph', flow, 'A', '0', 'taskmodule') == "siliconcompiler.tools.yosys.syn_asic"

@pytest.mark.quick
def test_import_tool():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    from siliconcompiler.tools.yosys import yosys
    chip.node(flow, 'A', yosys, 'syn_asic')

    assert chip.get('flowgraph', flow, 'A', '0', 'tool') == "yosys"
    assert chip.get('flowgraph', flow, 'A', '0', 'toolmodule') == "siliconcompiler.tools.yosys.yosys"
    assert chip.get('flowgraph', flow, 'A', '0', 'task') == "syn_asic"
    assert chip.get('flowgraph', flow, 'A', '0', 'taskmodule') == "siliconcompiler.tools.yosys.syn_asic"

@pytest.mark.quick
def test_import_task():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    from siliconcompiler.tools.yosys import yosys
    from siliconcompiler.tools.yosys import syn_asic
    chip.node(flow, 'A', yosys, syn_asic)

    assert chip.get('flowgraph', flow, 'A', '0', 'tool') == "yosys"
    assert chip.get('flowgraph', flow, 'A', '0', 'toolmodule') == "siliconcompiler.tools.yosys.yosys"
    assert chip.get('flowgraph', flow, 'A', '0', 'task') == "syn_asic"
    assert chip.get('flowgraph', flow, 'A', '0', 'taskmodule') == "siliconcompiler.tools.yosys.syn_asic"

@pytest.mark.quick
def test_string_task():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    from siliconcompiler.tools.yosys import yosys
    chip.node(flow, 'A', yosys, 'siliconcompiler.tools.yosys.syn_asic')

    assert chip.get('flowgraph', flow, 'A', '0', 'tool') == "yosys"
    assert chip.get('flowgraph', flow, 'A', '0', 'toolmodule') == "siliconcompiler.tools.yosys.yosys"
    assert chip.get('flowgraph', flow, 'A', '0', 'task') == "syn_asic"
    assert chip.get('flowgraph', flow, 'A', '0', 'taskmodule') == "siliconcompiler.tools.yosys.syn_asic"
