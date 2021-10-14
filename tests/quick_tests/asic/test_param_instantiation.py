import os
import siliconcompiler

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_parameterized_instantiation():
    '''Ensure that we can properly import and synthesize a multi-source design
    where module instantiation depends on parameter values.
    '''

    localdir = os.path.dirname(os.path.abspath(__file__))
    files = f'{localdir}/../../data/test_param_instantiation'

    chip = siliconcompiler.Chip()
    chip.target('asicflow_freepdk45')

    chip.add('source', f'{files}/wrapper.v')
    chip.add('source', f'{files}/gate.v')
    chip.add('source', f'{files}/and2.v')
    chip.add('source', f'{files}/or2.v')

    chip.set('steplist', ['import', 'syn'])
    
    # Test 1: gate as top-level, default parameter value
    design = 'gate'
    chip.set('design', design)
    chip.run()
    assert os.path.isfile(f"build/{design}/job0/syn/0/outputs/{design}.vg")

    # Test 2: wrapper as top-level, which changes parameter in Verilog
    design = 'wrapper'
    chip.set('design', design)
    chip.set('jobname', 'job1')
    chip.run()
    assert os.path.isfile(f"build/{design}/job1/syn/0/outputs/{design}.vg")

    # Test 3: gate as top-level again, but change parameter from SC
    design = 'gate'
    chip.set('design', design)
    chip.set('param', 'Impl', '1')
    chip.set('jobname', 'job2')
    chip.run()
    assert os.path.isfile(f"build/{design}/job2/syn/0/outputs/{design}.vg")

if __name__ == "__main__":
    test_parameterized_instantiation()
