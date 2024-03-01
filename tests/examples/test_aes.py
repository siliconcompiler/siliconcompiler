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

    from examples.aes import aes
    aes.rtl2gds()

    syn_verilog = 'build/aes/job0/syn/0/outputs/aes.vg'
    assert os.path.isfile(syn_verilog)
