import pytest
import os


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
@pytest.mark.asic_to_syn
def test_example():
    from examples.heartbeat_migen import heartbeat_migen
    heartbeat_migen.main()

    syn_verilog = 'build/heartbeat/job0/syn/0/outputs/heartbeat.vg'
    assert os.path.isfile(syn_verilog)
