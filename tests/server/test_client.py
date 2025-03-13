import os
import pytest


def test_failure_to_upload(gcd_chip, scserver_credential):
    '''
    Ensure the remote fails on file collection
    '''

    os.makedirs('dont_upload', exist_ok=True)
    gcd_chip.set('option', 'idir', 'dont_upload')
    gcd_chip.set('option', 'idir', True, field='copy')
    gcd_chip.set('option', 'credentials', scserver_credential(5000))
    gcd_chip.set('option', 'remote', True)

    # Run the remote job.
    with pytest.raises(RuntimeError):
        gcd_chip.run(raise_exception=True)
