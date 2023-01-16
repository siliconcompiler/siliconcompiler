# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import gzip
import os
import pytest
from pyvirtualdisplay import Display
import sys

from unittest import mock

def adjust_exe_options(chip, headless):
    if not headless:
        return

    for step in ('show', 'screenshot'):
        # adjust options to ensure programs exit
        for tool in ('klayout', 'openroad'):
            chip.set('tool', tool, 'var', step, '0', 'show_exit', 'true')

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
@pytest.mark.parametrize('tool', ['klayout', 'openroad'])
@pytest.mark.parametrize('project, testfile',
    [('freepdk45_demo', 'heartbeat_freepdk45.def'),
     ('skywater130_demo', 'heartbeat_sky130.def')])
def test_show(project, testfile, tool, datadir, display, headless=True):
    chip = siliconcompiler.Chip('heartbeat')
    chip.load_target(project)
    chip.set('option', "quiet", True)

    for ext in chip.getkeys('option', 'showtool'):
        chip.set('option', 'showtool', ext, tool)

    adjust_exe_options(chip, headless)

    path = os.path.join(datadir, testfile)
    assert chip.show(path)

@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.parametrize('tool', ['klayout', 'openroad'])
@pytest.mark.parametrize('project, testfile',
    [('freepdk45_demo', 'heartbeat_freepdk45.def'),
     ('skywater130_demo', 'heartbeat_sky130.def')])
def test_screenshot(project, testfile, tool, datadir, display, headless=True):
    chip = siliconcompiler.Chip('heartbeat')
    chip.load_target(project)
    chip.set('option', "quiet", True)

    for ext in chip.getkeys('option', 'showtool'):
        chip.set('option', 'showtool', ext, tool)

    adjust_exe_options(chip, headless)

    path = os.path.join(datadir, testfile)
    screenshot_path = chip.show(path, screenshot=True)
    assert screenshot_path
    assert os.path.exists(screenshot_path)

@pytest.mark.eda
@pytest.mark.quick
def test_show_lyp(datadir, display, headless=True):
    ''' Test sc-show with only a KLayout .lyp file for layer properties '''

    chip = siliconcompiler.Chip('heartbeat')
    chip.load_target(f'freepdk45_demo')
    chip.set('option', 'quiet', True)

    # Remove the '.lyt' file
    stackup = chip.get('asic', 'stackup')
    pdkname = chip.get('option', 'pdk')
    chip.set('pdk', pdkname, 'layermap', 'klayout', stackup, 'def', 'gds', None)

    adjust_exe_options(chip, headless)

    path = os.path.join(datadir, 'heartbeat_freepdk45.def')
    assert chip.show(path)

@pytest.mark.eda
@pytest.mark.quick
def test_show_nopdk(datadir, display):
    chip = siliconcompiler.Chip('heartbeat')
    chip.load_target('freepdk45_demo')
    chip.set('option', 'quiet', True)

    testfile = os.path.join(datadir, 'heartbeat.gds.gz')

    adjust_exe_options(chip, True)

    # For some reason, if we try to use monkeypath to modify the env, the
    # subprocess call performed by chip.show() doesn't use the patched env. We
    # use unittest.mock instead, since that behaves as desired.
    env = {'SCPATH': ''}
    with mock.patch.dict(os.environ, env):
        assert chip.show(testfile)

#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_show('freepdk45_demo', 'heartbeat_freepdk45.def', 'klayout', datadir(__file__),
              None, headless=True)
    test_show('skywater130_demo', 'heartbeat_sky130.def', 'klayout', datadir(__file__),
              None, headless=True)
    test_screenshot('skywater130_demo', 'heartbeat_sky130.def', 'openroad', datadir(__file__),
              None, headless=True)
    test_show_nopdk(datadir(__file__), None)
