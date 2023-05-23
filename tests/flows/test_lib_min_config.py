import os
import subprocess

import pytest


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_yosys_lib_preproc(gcd_chip):
    # Remove "cells" configs from the standard cell lib,
    # to simulate a minimal library configuration.
    gcd_chip.schema.cfg['library']['nangate45']['asic'].pop('cells')

    # Run the design's Yosys task; it should succeed.
    gcd_chip.set('option', 'steplist', ['import', 'syn'])
    gcd_chip.run()

    # Verify that synthesis output is generated.
    assert os.path.isfile('build/gcd/job0/syn/0/outputs/gcd.vg')
    assert os.path.isfile('build/gcd/job0/syn/0/outputs/gcd.pkg.json')
