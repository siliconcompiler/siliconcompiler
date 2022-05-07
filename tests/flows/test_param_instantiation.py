import os
import siliconcompiler
import pytest

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.skip(reason="not supported with each chip object having ummutable design name")
def test_parameterized_instantiation(datadir):
    '''Ensure that we can properly import and synthesize a multi-source design
    where module instantiation depends on parameter values.
    '''

    chip = siliconcompiler.Chip('gate')
    chip.load_target('freepdk45_demo')

    chip.add('source', 'verilog', os.path.join(datadir, 'test_param_instantiation', 'wrapper.v'))
    chip.add('source', 'verilog', os.path.join(datadir, 'test_param_instantiation', 'gate.v'))
    chip.add('source', 'verilog', os.path.join(datadir, 'test_param_instantiation', 'and2.v'))
    chip.add('source', 'verilog', os.path.join(datadir, 'test_param_instantiation', 'or2.v'))

    chip.set('option', 'steplist', ['import', 'syn'])

    # Test 1: gate as top-level, default parameter value
    design = 'gate'
    chip.set('design', design)
    chip.run()
    assert os.path.isfile(f"build/{design}/job0/syn/0/outputs/{design}.vg")

    # Test 2: wrapper as top-level, which changes parameter in Verilog
    design = 'wrapper'
    chip.set('design', design)
    chip.set('option', 'jobname', 'job1')
    chip.run()
    assert os.path.isfile(f"build/{design}/job1/syn/0/outputs/{design}.vg")

    # Test 3: gate as top-level again, but change parameter from SC
    design = 'gate'
    chip.set('design', design)
    chip.set('option', 'param', 'Impl', '1')
    chip.set('option', 'jobname', 'job2')
    chip.run()
    assert os.path.isfile(f"build/{design}/job2/syn/0/outputs/{design}.vg")

if __name__ == "__main__":
    from tests.fixtures import datadir
    test_parameterized_instantiation(datadir(__file__))
