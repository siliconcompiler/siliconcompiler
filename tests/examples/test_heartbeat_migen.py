import pytest
import os
import siliconcompiler


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(600)
def test_example(monkeypatch):
    org_init = siliconcompiler.Chip.__init__

    def _mock_init(chip, design, loglevel=None):
        org_init(chip, design, loglevel=loglevel)

        chip.set('option', 'to', 'syn')

    monkeypatch.setattr(siliconcompiler.Chip, '__init__', _mock_init)

    from examples.heartbeat_migen import heartbeat_migen
    heartbeat_migen.main()

    syn_verilog = 'build/heartbeat/job0/syn/0/outputs/heartbeat.vg'
    assert os.path.isfile(syn_verilog)
