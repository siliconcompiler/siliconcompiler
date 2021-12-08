# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import os
import pytest
from pyvirtualdisplay import Display
from unittest import mock

@pytest.fixture
def display():
    display = Display(visible=False)
    display.start()
    yield display
    display.stop()

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.parametrize('pdk, testfile',
    [('freepdk45', 'heartbeat_freepdk45.def'),
     ('skywater130', 'heartbeat_sky130.def')])
def test_show(pdk, testfile, datadir, display, headless=True):
    chip = siliconcompiler.Chip()
    chip.set('design', 'heartbeat')
    chip.target(f'asicflow_{pdk}')
    chip.set("quiet", True)

    if headless:
        # Adjust command line options to exit KLayout after run
        chip.set('eda', 'klayout', 'showdef', '0', 'option', ['-z', '-r'])

    path = os.path.join(datadir, testfile)
    assert chip.show(path)

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.skip(reason="fails to produce testfile on CI host")
def test_show_nopdk(datadir, display):
    chip = siliconcompiler.Chip()
    chip.set('design', 'heartbeat')
    chip.target(f'asicflow_freepdk45')
    chip.set("quiet", True)
    # Adjust command line options to exit KLayout after run
    chip.set('eda', 'klayout', 'showdef', '0', 'option', ['-z', '-r'])

    testfile = os.path.join(datadir, 'heartbeat_freepdk45.def')

    # For some reason, if we try to use monkeypath to modify the env, the
    # subprocess call performed by chip.show() doesn't use the patched env. We
    # use unittest.mock instead, since that behaves as desired.
    env = {'SCPATH': ''}
    with mock.patch.dict(os.environ, env):
        assert chip.show(testfile)

#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_show('freepdk45', 'heartbeat_freepdk45.def', datadir(__file__),
                   None, headless=False)
