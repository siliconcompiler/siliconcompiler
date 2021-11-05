# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import os
import pytest
from pyvirtualdisplay import Display

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
def test_show_file(pdk, testfile, datadir, display, headless=True):
    chip = siliconcompiler.Chip()
    chip.target(f'asicflow_{pdk}')
    chip.set("quiet", True)

    if headless:
        # Adjust command line options to exit KLayout after run
        chip.set('eda', 'klayout', 'showdef', '0', 'option', 'cmdline', ['-z', '-r'])

    path = os.path.join(datadir, testfile)
    assert chip.show_file(path)

#########################
if __name__ == "__main__":
    from tests.fixtures import datadir
    test_show_file('freepdk45', 'heartbeat_freepdk45.def', datadir(__file__),
                   None, headless=False)
