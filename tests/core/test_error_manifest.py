import siliconcompiler
from siliconcompiler.tools.surelog import parse
from siliconcompiler._common import SiliconCompilerError
import os
from siliconcompiler.targets import freepdk45_demo


def test_error_manifest():
    '''
    Executing a node with errors should still produce an output manifest
    '''
    chip = siliconcompiler.Chip('test')
    chip.set('input', 'rtl', 'verilog', 'fake.v')
    chip.use(freepdk45_demo)
    flow = 'test'
    chip.set('option', 'flow', flow)
    step = 'import'
    index = '0'
    chip.node(flow, step, parse, index=index)

    try:
        chip.run()
    except SiliconCompilerError:
        workdir = chip.getworkdir(step=step, index=index)
        cfg = os.path.join(workdir, 'outputs', f'{chip.top()}.pkg.json')
        assert os.path.isfile(cfg)
