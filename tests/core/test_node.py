import pytest

import siliconcompiler
from siliconcompiler.tools.builtin import join
from siliconcompiler.flows import asicflow


def test_builtin():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    chip.node(flow, 'A', join)

    assert chip.get('flowgraph', flow, 'A', '0', 'tool') == "builtin"
    assert chip.get('flowgraph', flow, 'A', '0', 'task') == "join"


def test_import_task():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    from siliconcompiler.tools.yosys import syn_asic
    chip.node(flow, 'A', syn_asic)

    assert chip.get('flowgraph', flow, 'A', '0', 'tool') == "yosys"
    assert chip.get('flowgraph', flow, 'A', '0', 'task') == "syn_asic"
    assert chip.get('flowgraph', flow, 'A', '0', 'taskmodule') == \
        "siliconcompiler.tools.yosys.syn_asic"


def test_string_task():
    chip = siliconcompiler.Chip('test')
    flow = 'test'
    chip.node(flow, 'A', 'siliconcompiler.tools.yosys.syn_asic')

    assert chip.get('flowgraph', flow, 'A', '0', 'tool') == "yosys"
    assert chip.get('flowgraph', flow, 'A', '0', 'task') == "syn_asic"
    assert chip.get('flowgraph', flow, 'A', '0', 'taskmodule') == \
        "siliconcompiler.tools.yosys.syn_asic"


def test_remove_node_one_index():
    chip = siliconcompiler.Chip('test')
    chip.use(asicflow, place_np=3)

    chip.remove_node('asicflow', 'place.global', '1')

    assert '0' in chip.getkeys('flowgraph', 'asicflow', 'place.global')
    assert '1' not in chip.getkeys('flowgraph', 'asicflow', 'place.global')
    assert '2' in chip.getkeys('flowgraph', 'asicflow', 'place.global')

    assert chip.get('flowgraph', 'asicflow', field="schema").validate()


def test_remove_node_all_index():
    chip = siliconcompiler.Chip('test')
    chip.use(asicflow, place_np=3)

    chip.remove_node('asicflow', 'place.global')

    assert 'place.global' not in chip.getkeys('flowgraph', 'asicflow')

    assert chip.get('flowgraph', 'asicflow', field="schema").validate()


def test_remove_node_no_step():
    chip = siliconcompiler.Chip('test')
    chip.use(asicflow, place_np=3)

    with pytest.raises(ValueError,
                       match='place.g0lobal is not a valid step in asicflow'):
        chip.remove_node('asicflow', 'place.g0lobal')


def test_remove_node_no_index():
    chip = siliconcompiler.Chip('test')
    chip.use(asicflow, place_np=3)

    with pytest.raises(ValueError,
                       match='4 is not a valid index for place.global in asicflow'):
        chip.remove_node('asicflow', 'place.global', '4')


def test_remove_node_no_flow():
    chip = siliconcompiler.Chip('test')
    chip.use(asicflow, place_np=3)

    with pytest.raises(ValueError,
                       match='asic1flow is not in the manifest'):
        chip.remove_node('asic1flow', 'place.global')
