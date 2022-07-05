# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import os
import siliconcompiler

import pytest

@pytest.mark.eda
def test_steplist_repeat(gcd_chip, capfd):
    '''Regression test for #458.'''
    with capfd.disabled():
        gcd_chip.set('option', 'steplist', ['import', 'syn', 'floorplan'])
        gcd_chip.run()
        gcd_chip.set('option', 'steplist', ['syn'])
        gcd_chip.run()

    gcd_chip.summary()
    stdout, _ = capfd.readouterr()
    print(stdout)

    assert 'import0' not in stdout
    assert 'syn0' in stdout
    assert 'floorplan0' not in stdout
