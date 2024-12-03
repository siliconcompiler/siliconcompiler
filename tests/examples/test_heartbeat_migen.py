import pytest
import os


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_py_heartbeat_migen():
    from heartbeat_migen import heartbeat_migen
    heartbeat_migen.main()

    gds = 'build/heartbeat/job0/write.gds/0/outputs/heartbeat.gds'
    assert os.path.isfile(gds)
