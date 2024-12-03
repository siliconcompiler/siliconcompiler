import os
import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(900)
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
    assert os.path.isfile('build/gcd/job0/write.gds/0/outputs/gcd.gds')


if __name__ == "__main__":
    from tests.fixtures import gcd_chip
    test_slurm_local_py(gcd_chip())
