# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import pytest


@pytest.mark.eda
def test_from_to_repeat(gcd_chip, capfd):
    '''Regression test for #458.'''
    with capfd.disabled():
        gcd_chip.set('option', 'to', ['floorplan.init'])
        gcd_chip.run()
        gcd_chip.set('option', 'from', ['syn'])
        gcd_chip.set('option', 'to', ['syn'])
        gcd_chip.run()

    gcd_chip.summary()
    stdout, _ = capfd.readouterr()
    print(stdout)

    assert 'import.verilog0' in stdout
    assert 'syn0' in stdout
    assert 'floorplan.init0' not in stdout
