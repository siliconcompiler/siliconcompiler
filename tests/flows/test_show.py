# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import os
import platform
import pytest
from pyvirtualdisplay import Display
import sys
from siliconcompiler.tools.klayout import show as klayout_show
from siliconcompiler.tools.openroad import show as openroad_show
from siliconcompiler.tools.klayout import screenshot as klayout_screenshot
from siliconcompiler.tools.openroad import screenshot as openroad_screenshot
from siliconcompiler.targets import freepdk45_demo, skywater130_demo


def adjust_exe_options(chip, headless):
    if not headless:
        return

    for step in ('show', 'screenshot'):
        # adjust options to ensure programs exit
        for tool in ('klayout', 'openroad', 'gtkwave'):
            chip.set('tool', tool, 'task', step, 'var', 'show_exit', 'true')


@pytest.fixture
def display():
    if "WSL2" in platform.platform():
        os.environ["PYVIRTUALDISPLAY_DISPLAYFD"] = "0"

    if sys.platform != 'win32':
        display = Display(visible=False)
        display.start()
        yield display
        display.stop()
    else:
        yield False


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.parametrize('task', [klayout_show, openroad_show])
@pytest.mark.parametrize('target, testfile',
                         [(freepdk45_demo, 'heartbeat_freepdk45.def'),
                          (skywater130_demo, 'heartbeat_sky130.def')])
def test_show_def(target, testfile, task, datadir, display, headless=True):
    chip = siliconcompiler.Chip('heartbeat')
    chip.use(target)

    chip.register_showtool('def', task)

    adjust_exe_options(chip, headless)

    path = os.path.join(datadir, testfile)
    assert chip.show(path)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.parametrize('task', [klayout_screenshot, openroad_screenshot])
@pytest.mark.parametrize('target, testfile',
                         [(freepdk45_demo, 'heartbeat_freepdk45.def'),
                          (skywater130_demo, 'heartbeat_sky130.def')])
def test_screenshot_def(target, testfile, task, datadir, display, headless=True):
    chip = siliconcompiler.Chip('heartbeat')
    chip.use(target)

    chip.register_showtool('def', task)

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
    chip.use(freepdk45_demo)

    chip.register_showtool('def', klayout_show)

    # Remove the '.lyt' file
    stackup = chip.get('option', 'stackup')
    pdkname = chip.get('option', 'pdk')
    chip.set('pdk', pdkname, 'layermap', 'klayout', 'def', 'klayout', stackup, [])

    adjust_exe_options(chip, headless)

    path = os.path.join(datadir, 'heartbeat_freepdk45.def')
    assert chip.show(path)


@pytest.mark.eda
@pytest.mark.quick
def test_show_nopdk(datadir, display):
    chip = siliconcompiler.Chip('heartbeat')
    chip.use(freepdk45_demo)

    testfile = os.path.join(datadir, 'heartbeat.gds.gz')

    adjust_exe_options(chip, True)

    assert chip.show(testfile)


@pytest.mark.eda
@pytest.mark.quick
def test_show_vcd(datadir, display):
    chip = siliconcompiler.Chip('heartbeat')

    testfile = os.path.join(datadir, 'random.vcd')

    adjust_exe_options(chip, True)

    assert chip.show(testfile)


@pytest.mark.eda
@pytest.mark.quick
def test_screenshot_dot(datadir):
    chip = siliconcompiler.Chip('mkDotProduct_nt_Int32')

    testfile = os.path.join(datadir, 'mkDotProduct_nt_Int32.dot')

    assert os.path.exists(chip.show(testfile, screenshot=True))
