import pytest

import os.path


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_py_heartbeat_migen():
    from heartbeat_migen import heartbeat_migen
    heartbeat_migen.main()

    assert os.path.isfile('build/heartbeat/job0/write.gds/0/outputs/heartbeat.gds.gz')
