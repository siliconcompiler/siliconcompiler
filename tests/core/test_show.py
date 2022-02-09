# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import gzip
import os
import pytest
from pyvirtualdisplay import Display
import sys

from unittest import mock

@pytest.fixture
def display():
    if sys.platform != 'win32':
        display = Display(visible=False)
        display.start()
        yield display
        display.stop()
    else:
        yield False

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.parametrize('project, testfile',
    [('freepdk45_demo', 'heartbeat_freepdk45.def'),
     ('skywater130_demo', 'heartbeat_sky130.def')])
def test_show(project, testfile, datadir, display, headless=True):
    chip = siliconcompiler.Chip()
    chip.set('design', 'heartbeat')
    chip.load_target(project)
    chip.set("quiet", True)

    if headless:
        # Adjust command line options to exit KLayout after run
        chip.set('eda', 'klayout', 'option', 'showdef', '0', ['-z', '-r'])

    path = os.path.join(datadir, testfile)
    assert chip.show(path)

@pytest.mark.eda
@pytest.mark.quick
def test_show_lyp(datadir, display, headless=True):
    ''' Test sc-show with only a KLayout .lyp file for layer properties '''

    chip = siliconcompiler.Chip()
    chip.set('design', 'heartbeat')
    chip.load_target(f'freepdk45_demo')
    chip.set("quiet", True)

    # Replace the '.lyt' file with the corresponding '.lyp'
    stackup = chip.get('pdk', 'stackup')[0]
    klayout_techfile = chip.get('pdk', 'layermap', 'klayout', stackup, 'def', 'gds')[0]
    klayout_layerprops = klayout_techfile[:-4] + '.lyp'
    chip.set('pdk', 'layermap', 'klayout', stackup, 'def', 'gds', klayout_layerprops, clobber=True)

    if headless:
        # Adjust command line options to exit KLayout after run
        chip.set('eda', 'klayout', 'option', 'showdef', '0', ['-z', '-r'])

    path = os.path.join(datadir, 'heartbeat_freepdk45.def')
    assert chip.show(path)

@pytest.mark.eda
@pytest.mark.quick
def test_show_nopdk(datadir, display):
    chip = siliconcompiler.Chip()
    chip.set('design', 'heartbeat')
    chip.load_target('freepdk45_demo')
    chip.set("quiet", True)
    # Adjust command line options to exit KLayout after run
    chip.set('eda', 'klayout', 'option', 'showgds', '0', ['-z', '-r'])

    # uncompress test file
    testfile = 'heartbeat.gds'
    with gzip.open(os.path.join(datadir, 'heartbeat.gds.gz'), 'rb') as gds_gz:
        with open(testfile, 'wb') as gds:
            gds.write(gds_gz.read())

    # For some reason, if we try to use monkeypath to modify the env, the
    # subprocess call performed by chip.show() doesn't use the patched env. We
    # use unittest.mock instead, since that behaves as desired.
    env = {'SCPATH': ''}
    with mock.patch.dict(os.environ, env):
        assert chip.show(testfile)

#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_show('freepdk45_demo', 'heartbeat_freepdk45.def', datadir(__file__),
                   None, headless=False)
    test_show('skywater130_demo', 'heartbeat_skywater130.def', datadir(__file__),
                   None, headless=False)
