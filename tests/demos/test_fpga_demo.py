import pytest

import os.path

from siliconcompiler.demos import fpga_demo


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.timeout(300)
def test_self_test():
    ''' Verify self-test functionality w/ Python build script '''
    proj = fpga_demo.FPGADemo()
    assert proj.run()
    assert os.path.isfile('build/heartbeat/job0/bitstream/0/outputs/heartbeat.fasm')
