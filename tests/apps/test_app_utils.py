import os
from siliconcompiler.apps.utils import summarize

import pytest


@pytest.mark.eda
@pytest.mark.quick
def test_summarize_cfg(monkeypatch, gcd_chip):
    '''Tests that sc summarizes a cfg.'''

    gcd_chip.run()
    gcd_chip.write_manifest('test.json')

    assert os.path.isfile('test.json')

    monkeypatch.setattr('sys.argv', [summarize.__name__, '-cfg', 'test.json'])
    assert summarize.main() == 0
