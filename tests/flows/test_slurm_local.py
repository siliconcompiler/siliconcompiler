import os
import pytest

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_slurm_local_py(gcd_chip):
    '''Basic Python API test: build the GCD example using only Python code.
       Note: Requires that the test runner be connected to a cluster, or configured
       as a single-machine "cluster".
    '''

    # Inserting value into configuration
    gcd_chip.set('option', 'scheduler', 'name', 'slurm')

    # Run the chip's build process synchronously.
    gcd_chip.run()

    # Verify that GDS file was generated.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
@pytest.mark.skip(reason='Skipped until test can be fixed')
def test_slurm_local_py_script_override(gcd_chip):
    '''Basic Python API test: build the GCD example using only Python code.
       Note: Requires that the test runner be connected to a cluster, or configured
       as a single-machine "cluster".
    '''

    # Inserting value into configuration
    gcd_chip.set('option', 'scheduler', 'name', 'slurm')
    os.makedirs('build/configs')
    gcd_chip.write_manifest('build/configs/import0.json')
    with open('build/configs/import0.sh', 'w') as slurm_script:
        slurm_script.write('#!/bin/bash\ntouch inputs/extrafile.txt\n')

    # Defer the import0 task to the cluster, which should run the overridden task script.
    gcd_chip._defertask('import', '0', {'job_hash': '1234abcd'})

    # Verify that GDS file was generated.
    assert os.path.isfile('build/gcd/job0/import/0/inputs/extrafile.txt')


if __name__ == "__main__":
    from tests.fixtures import gcd_chip
    test_slurm_local_py(gcd_chip())
