import siliconcompiler
from siliconcompiler.targets import freepdk45_demo


def test_check_flowgraph_steplist_not_set():
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
