import os
import sys

import siliconcompiler.report.dashboard.cli.keyboard as keyboard_mod


# Platform-independent tests
def test_check_key_none(monkeypatch):
    # Simulate no key pressed
    if os.name == 'nt':
        monkeypatch.setattr(keyboard_mod.msvcrt, 'kbhit', lambda: False)
        assert keyboard_mod.check_key() is None
    else:
        monkeypatch.setattr(keyboard_mod.select, 'select', lambda x, y, z, w=None: ([], [], []))
        assert keyboard_mod.check_key() is None


def test_check_key_pressed(monkeypatch):
    # Simulate key pressed
    if os.name == 'nt':
        monkeypatch.setattr(keyboard_mod.msvcrt, 'kbhit', lambda: True)
        monkeypatch.setattr(keyboard_mod.msvcrt, 'getch', lambda: b'a')
        assert keyboard_mod.check_key() == 'a'
    else:
        monkeypatch.setattr(keyboard_mod.select, 'select', lambda x, y, z, w=None: ([sys.stdin], [], []))
        monkeypatch.setattr(sys.stdin, 'read', lambda n: 'b')
        assert keyboard_mod.check_key() == 'b'


def test_keyboard_start_stop(monkeypatch):
    if os.name != 'nt':
        # Mock termios and tty
        monkeypatch.setattr(keyboard_mod.termios, 'tcgetattr', lambda x: 'settings')
        monkeypatch.setattr(keyboard_mod.tty, 'setcbreak', lambda x: None)
        monkeypatch.setattr(keyboard_mod.sys.stdin, 'fileno', lambda: 0)
        keyboard_mod.Keyboard.start()
        assert hasattr(keyboard_mod.Keyboard, 'old_settings')
        monkeypatch.setattr(keyboard_mod.termios, 'tcsetattr', lambda x, y, z: None)
        keyboard_mod.Keyboard.stop()
    else:
        # Should not raise
        keyboard_mod.Keyboard.start()
        keyboard_mod.Keyboard.stop()


def test_keyboard_check_key(monkeypatch):
    # Should delegate to module-level check_key
    if os.name == 'nt':
        monkeypatch.setattr(keyboard_mod.msvcrt, 'kbhit', lambda: True)
        monkeypatch.setattr(keyboard_mod.msvcrt, 'getch', lambda: b'x')
        assert keyboard_mod.Keyboard.check_key() == 'x'
    else:
        monkeypatch.setattr(keyboard_mod.select, 'select', lambda x, y, z, w=None: ([sys.stdin], [], []))
        monkeypatch.setattr(sys.stdin, 'read', lambda n: 'y')
        assert keyboard_mod.Keyboard.check_key() == 'y'
