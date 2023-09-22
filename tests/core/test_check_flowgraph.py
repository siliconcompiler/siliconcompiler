import siliconcompiler
from siliconcompiler.targets import freepdk45_demo
from siliconcompiler.tools.yosys import syn_asic
from siliconcompiler.tools.surelog import parse


def test_check_flowgraph_from_to_not_set():
    chip = siliconcompiler.Chip('foo')
    chip.load_target(freepdk45_demo)

    assert chip._check_flowgraph()


def test_check_flowgraph_extra_from_steps():
    chip = siliconcompiler.Chip('foo')
    chip.load_target(freepdk45_demo)

    chip.set('option', 'from', ['syn2'])

    assert not chip._check_flowgraph()


def test_check_flowgraph_extra_to_steps():
    chip = siliconcompiler.Chip('foo')
    chip.load_target(freepdk45_demo)

    chip.set('option', 'to', ['syn2'])

    assert not chip._check_flowgraph()


def test_check_flowgraph_disjoint():
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'rtl', 'verilog', 'fake.v')
    chip.load_target('freepdk45_demo')
    chip.set('option', 'mode', 'asic')
    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', parse)
    chip.node(flow, 'syn', syn_asic)
    chip.set('option', 'from', 'import')
    chip.set('option', 'to', 'syn')

    assert not chip._check_flowgraph()
