import os
import pytest

@pytest.mark.eda
def test_slurm_local_py(gcd_chip):
    '''Basic Python API test: build the GCD example using only Python code.
       Note: Requires that the test runner be connected to a cluster, or configured
       as a single-machine "cluster".
    '''

    # Inserting value into configuration
    gcd_chip.set('option', 'scheduler', 'slurm')

    # Run the chip's build process synchronously.
    gcd_chip.run()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')

@pytest.mark.eda
def test_slurm_local_py_prefix(gcd_chip):
    '''Basic Python API test: build the GCD example using only Python code.
       Note: Requires that the test runner be connected to a cluster, or configured
       as a single-machine "cluster".
    '''

    # Inserting value into configuration
    gcd_chip.set('option', 'scheduler', 'slurm')
    gcd_chip.status['syn0_sched_preprocess'] = '''
touch inputs/extrafile.txt
'''

    # Run the chip's build process synchronously.
    gcd_chip.run()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')
    assert os.path.isfile('build/gcd/job0/syn/0/inputs/extrafile.txt')

@pytest.mark.eda
def test_slurm_local_py_suffix(gcd_chip):
    '''Basic Python API test: build the GCD example using only Python code.
       Note: Requires that the test runner be connected to a cluster, or configured
       as a single-machine "cluster".
    '''

    # Inserting value into configuration
    gcd_chip.set('option', 'scheduler', 'slurm')
    gcd_chip.status['sched_postprocess'] = '''
touch outputs/extrafile.txt
'''
    gcd_chip.status['place0_sched_postprocess'] = '''
touch outputs/placefile.txt
'''

    # Run the chip's build process synchronously.
    gcd_chip.run()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')
    # Verify that post-process blocks ran correctly.
    assert os.path.isfile('build/gcd/job0/syn/0/outputs/extrafile.txt')
    assert os.path.isfile('build/gcd/job0/floorplan/0/outputs/extrafile.txt')
    assert os.path.isfile('build/gcd/job0/place/0/outputs/extrafile.txt')
    assert os.path.isfile('build/gcd/job0/place/0/outputs/placefile.txt')

if __name__ == "__main__":
    from tests.fixtures import gcd_chip
    test_slurm_local_py(gcd_chip())
