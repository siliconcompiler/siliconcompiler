import siliconcompiler
import os
from siliconcompiler.tools.builtin import nop
from unittest.mock import patch


names_to_remove = {'DISPLAY', 'WAYLAND_DISPLAY'}
modified_environ = {k: v for k, v in os.environ.items() if k not in names_to_remove}


@patch('sys.platform', 'linux')
def test_check_display_run():
    # Checks if _check_display() is called during run()
    chip = siliconcompiler.Chip('test')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    chip.set('option', 'mode', 'asic')
    with patch.dict(os.environ, modified_environ, clear=True):
        chip.run()
        assert chip.get('option', 'nodisplay')


@patch('sys.platform', 'linux')
def test_check_display_nodisplay():
    # Checks if the nodisplay option is set
    # On linux system without display
    with patch.dict(os.environ, modified_environ, clear=True):
        chip = siliconcompiler.Chip('test')
        chip._check_display()
        assert chip.get('option', 'nodisplay')


@patch('sys.platform', 'linux')
@patch.dict(os.environ, {'DISPLAY': ':0'})
def test_check_display_with_display_x11():
    # Checks that the nodisplay option is not set
    # On linux system with X11 disp
    chip = siliconcompiler.Chip('test')
    chip._check_display()
    assert not chip.get('option', 'nodisplay')


@patch('sys.platform', 'linux')
@patch.dict(os.environ, {'WAYLAND_DISPLAY': 'wayland-0'})
def test_check_display_with_display_wayland():
    # Checks that the nodisplay option is not set
    # On linux system with Wayland display
    chip = siliconcompiler.Chip('test')
    chip._check_display()
    assert not chip.get('option', 'nodisplay')


@patch('sys.platform', 'darwin')
def test_check_display_with_display_macos():
    # Checks that the nodisplay option is not set
    # On macos system
    with patch.dict(os.environ, modified_environ, clear=True):
        chip = siliconcompiler.Chip('test')
        chip._check_display()
        assert not chip.get('option', 'nodisplay')


@patch('sys.platform', 'win32')
def test_check_display_with_display_windows():
    # Checks that the nodisplay option is not set
    # On windows system
    with patch.dict(os.environ, modified_environ, clear=True):
        chip = siliconcompiler.Chip('test')
        chip._check_display()
        assert not chip.get('option', 'nodisplay')
