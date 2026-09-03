import subprocess
import sys

import pytest


@pytest.mark.parametrize('demo', ('asic_demo', 'fpga_demo'))
@pytest.mark.parametrize('switch', ('-remote', '-scheduler'))
def test_demo_accepts_switch(demo, switch):
    '''The demos' command lines are what the README and installation docs tell
    people to run, so the switchlist they expose is part of that contract.'''

    usage = subprocess.run(
        [sys.executable, '-m', f'siliconcompiler.demos.{demo}', '-h'],
        capture_output=True, text=True, check=True).stdout

    assert switch in usage
