import siliconcompiler
from siliconcompiler.scheduler import _check_display
import os
import sys
from siliconcompiler.tools.builtin import nop
from unittest.mock import patch
import pytest


@pytest.fixture
def modified_environ():
    names_to_remove = {'DISPLAY', 'WAYLAND_DISPLAY'}
    return {k: v for k, v in os.environ.items() if k not in names_to_remove}


def test_check_display_run(modified_environ):
    # Checks if _check_display() is called during run()
    chip = siliconcompiler.Chip('test')

    flow = 'test'
    chip.set('option', 'flow', flow)
    chip.node(flow, 'import', nop)
    with patch.dict(os.environ, modified_environ, clear=True):
        chip.run()
        if sys.platform == 'linux':
            assert chip.get('option', 'nodisplay')
        else:
            # no changes
            assert not chip.get('option', 'nodisplay')


@patch('sys.platform', 'linux')
def test_check_display_nodisplay(modified_environ):
    # Checks if the nodisplay option is set
    # On linux system without display
    with patch.dict(os.environ, modified_environ, clear=True):
        chip = siliconcompiler.Chip('test')
        _check_display(chip)
        assert chip.get('option', 'nodisplay')


@patch('sys.platform', 'linux')
@patch.dict(os.environ, {'DISPLAY': ':0'})
def test_check_display_with_display_x11():
    # Checks that the nodisplay option is not set
    # On linux system with X11 disp
    chip = siliconcompiler.Chip('test')
    _check_display(chip)
    assert not chip.get('option', 'nodisplay')


@patch('sys.platform', 'linux')
@patch.dict(os.environ, {'WAYLAND_DISPLAY': 'wayland-0'})
def test_check_display_with_display_wayland():
    # Checks that the nodisplay option is not set
    # On linux system with Wayland display
    chip = siliconcompiler.Chip('test')
    _check_display(chip)
    assert not chip.get('option', 'nodisplay')


@patch('sys.platform', 'darwin')
def test_check_display_with_display_macos(modified_environ):
    # Checks that the nodisplay option is not set
    # On macos system
    with patch.dict(os.environ, modified_environ, clear=True):
        chip = siliconcompiler.Chip('test')
        _check_display(chip)
        assert not chip.get('option', 'nodisplay')


@patch('sys.platform', 'win32')
def test_check_display_with_display_windows(modified_environ):
    # Checks that the nodisplay option is not set
    # On windows system
    with patch.dict(os.environ, modified_environ, clear=True):
        chip = siliconcompiler.Chip('test')
        _check_display(chip)
        assert not chip.get('option', 'nodisplay')
