import os
import siliconcompiler
from siliconcompiler.apps import sc

import pytest
from siliconcompiler.targets import asic_demo


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_self_test():
    ''' Verify self-test functionality w/ Python build script '''
    chip = siliconcompiler.Chip('')
    chip.use(asic_demo)
    chip.run()
    assert os.path.isfile('build/heartbeat/job0/write.gds/0/outputs/heartbeat.gds')
    assert chip.get('metric', 'holdslack', step='write.views', index='0') >= 0.0
    assert chip.get('metric', 'holdslack', step='write.views', index='0') < 10.0
    assert chip.get('metric', 'setupslack', step='write.views', index='0') >= 0.0
    assert chip.get('metric', 'setupslack', step='write.views', index='0') < 10.0


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_self_test_cli(monkeypatch):
    ''' Verify self-test functionality w/ command-line call '''
    monkeypatch.setattr('sys.argv', ['sc', '-target', 'asic_demo'])
    assert sc.main() == 0

    assert os.path.isfile('build/heartbeat/job0/write.gds/0/outputs/heartbeat.gds')
    assert os.path.isfile('build/heartbeat/job0/heartbeat.pkg.json')

    # Check timing
    chip = siliconcompiler.Chip('')
    chip.read_manifest('build/heartbeat/job0/heartbeat.pkg.json')
    assert chip.get('metric', 'holdslack', step='write.views', index='0') >= 0.0
    assert chip.get('metric', 'holdslack', step='write.views', index='0') < 10.0
    assert chip.get('metric', 'setupslack', step='write.views', index='0') >= 0.0
    assert chip.get('metric', 'setupslack', step='write.views', index='0') < 10.0
