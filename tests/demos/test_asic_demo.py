import pytest

import os.path

from siliconcompiler.demos import asic_demo


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.ready
@pytest.mark.timeout(300)
def test_self_test():
    ''' Verify self-test functionality w/ Python build script '''
    proj = asic_demo.ASICDemo()
    assert proj.run()
    assert os.path.isfile('build/heartbeat/job0/write.gds/0/outputs/heartbeat.gds')
    assert proj.history("job0").get('metric', 'holdslack', step='write.views', index='0') >= 0.0
    assert proj.history("job0").get('metric', 'holdslack', step='write.views', index='0') < 10.0
    assert proj.history("job0").get('metric', 'setupslack', step='write.views', index='0') >= 0.0
    assert proj.history("job0").get('metric', 'setupslack', step='write.views', index='0') < 10.0
