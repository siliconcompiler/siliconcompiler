import os
import siliconcompiler
import pytest
from siliconcompiler.targets import freepdk45_demo


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(180)
def test_parameterized_instantiation(datadir):
    '''Ensure that we can properly import and synthesize a multi-source design
    where module instantiation depends on parameter values.
    '''

    chip = siliconcompiler.Chip('gate')
    chip.use(freepdk45_demo)

    chip.input(os.path.join(datadir, 'test_param_instantiation', 'wrapper.v'))
    chip.input(os.path.join(datadir, 'test_param_instantiation', 'gate.v'))
    chip.input(os.path.join(datadir, 'test_param_instantiation', 'and2.v'))
    chip.input(os.path.join(datadir, 'test_param_instantiation', 'or2.v'))

    chip.set('option', 'to', ['syn'])

    # Test 1: gate as top-level, default parameter value
    design = 'gate'
    chip.set('design', design)
    assert chip.run()
    assert os.path.isfile(f"build/{design}/job0/syn/0/outputs/{design}.vg")

    # Test 2: wrapper as top-level, which changes parameter in Verilog
    design = 'wrapper'
    chip.set('design', design)
    chip.set('option', 'jobname', 'job1')
    assert chip.run()
    assert os.path.isfile(f"build/{design}/job1/syn/0/outputs/{design}.vg")

    # Test 3: gate as top-level again, but change parameter from SC
    design = 'gate'
    chip.set('design', design)
    chip.set('option', 'param', 'Impl', '1')
    chip.set('option', 'jobname', 'job2')
    assert chip.run()
    assert os.path.isfile(f"build/{design}/job2/syn/0/outputs/{design}.vg")
