import os
import siliconcompiler
from ...fixtures import test_wrapper

import pytest

##################################
def test_failure_notquiet():
    '''Test that SC exits early on errors without -quiet switch.

    This is a regression test for an issue where SC would only exit early on a
    command failure in cases where the -quiet switch was included.
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip(loglevel='NOTSET')

    # Inserting value into configuration
    chip.add('source', '../tests/fpga/test_failure/bad.v')
    chip.add('design', 'bad')
    chip.set('target', "ice40_nextpnr")
    chip.set_jobid()

    chip.target()

    chip.set('stop', 'syn')

    # Expect that command exits early
    with pytest.raises(SystemExit):
        chip.run()

    # Expect that we didn't reach synthesis step
    assert not os.path.isdir('build/bad/job1/syn')

def test_failure_quiet():
    '''Test that SC exits early on errors with -quiet switch.
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip(loglevel='NOTSET')

    # Inserting value into configuration
    chip.add('source', '../tests/fpga/test_failure/bad.v')
    chip.add('design', 'bad')
    chip.set('target', "ice40_nextpnr")
    chip.set_jobid()

    chip.target()

    chip.set('stop', 'syn')
    chip.set('quiet', 'true')

    # Expect that command exits early
    with pytest.raises(SystemExit):
        chip.run()

    # Expect that we didn't reach synthesis step
    assert not os.path.isdir('build/bad/job1/syn')
