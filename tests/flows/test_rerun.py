# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import pytest


@pytest.mark.eda
def test_from_to_repeat(gcd_chip, capfd):
    '''Regression test for #458.'''
    with capfd.disabled():
        gcd_chip.set('option', 'to', ['floorplan.init'])
        assert gcd_chip.run()
        gcd_chip.set('option', 'from', ['syn'])
        gcd_chip.set('option', 'to', ['syn'])
        assert gcd_chip.run()

    gcd_chip.summary()
    stdout, _ = capfd.readouterr()
    print(stdout)

    assert 'import.veri...0' in stdout
    assert 'syn/0' in stdout
    assert 'floorplan.init/0' not in stdout
