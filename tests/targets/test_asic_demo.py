import pytest

import os.path

from siliconcompiler import ASICProject

from siliconcompiler.targets import asic_demo


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.timeout(300)
def test_self_test():
    ''' Verify self-test functionality w/ Python build script '''
    proj = ASICProject()
    proj.load_target(asic_demo.setup)
    assert proj.run()
    assert os.path.isfile('build/heartbeat/job0/write.gds/0/outputs/heartbeat.gds')
    assert proj.get('metric', 'holdslack', step='write.views', index='0') >= 0.0
    assert proj.get('metric', 'holdslack', step='write.views', index='0') < 10.0
    assert proj.get('metric', 'setupslack', step='write.views', index='0') >= 0.0
    assert proj.get('metric', 'setupslack', step='write.views', index='0') < 10.0
