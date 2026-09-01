import os
import pytest
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
        monkeypatch.setattr(keyboard_mod.select, 'select',
                            lambda x, y, z, w=None: ([sys.stdin], [], []))
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


def test_keyboard_check_key_without_start(monkeypatch):
    # Should delegate to module-level check_key
    if os.name == 'nt':
        monkeypatch.setattr(keyboard_mod.msvcrt, 'kbhit', lambda: True)
        monkeypatch.setattr(keyboard_mod.msvcrt, 'getch', lambda: b'x')
        assert keyboard_mod.Keyboard.check_key() is None
        assert keyboard_mod.Keyboard.enabled is False
    else:
        monkeypatch.setattr(keyboard_mod.select, 'select',
                            lambda x, y, z, w=None: ([sys.stdin], [], []))
        monkeypatch.setattr(sys.stdin, 'read', lambda n: 'y')
        assert keyboard_mod.Keyboard.check_key() is None
        assert keyboard_mod.Keyboard.enabled is False


def test_keyboard_check_key_with_start(monkeypatch):
    # Should delegate to module-level check_key
    keyboard_mod.Keyboard.enabled = True

    if os.name == 'nt':
        monkeypatch.setattr(keyboard_mod.msvcrt, 'kbhit', lambda: True)
        monkeypatch.setattr(keyboard_mod.msvcrt, 'getch', lambda: b'x')
        assert keyboard_mod.Keyboard.check_key() == 'x'
    else:
        monkeypatch.setattr(keyboard_mod.select, 'select',
                            lambda x, y, z, w=None: ([sys.stdin], [], []))
        monkeypatch.setattr(sys.stdin, 'read', lambda n: 'y')
        assert keyboard_mod.Keyboard.check_key() == 'y'


@pytest.mark.skipif(os.name == 'nt', reason="termios is POSIX only")
def test_keyboard_start_non_tty_stdin_does_not_raise(monkeypatch):
    """A stdin that is not a terminal must disable hotkeys, not fail the run.

    ``termios.error`` does not subclass ``OSError`` -- its MRO is
    ``(termios.error, Exception, BaseException, object)`` -- so guarding the
    probe with ``except OSError`` missed the one case it was written for.
    Every ``multiprocessing`` worker is handed /dev/null on stdin, as is
    anything under nohup, cron or a CI runner that closes stdin, so this used
    to take down every concurrent ``Project.run()`` that opened a dashboard.
    """
    def not_a_tty(_):
        raise keyboard_mod.termios.error(25, 'Inappropriate ioctl for device')

    monkeypatch.setattr(keyboard_mod.termios, 'tcgetattr', not_a_tty)
    monkeypatch.delattr(keyboard_mod.Keyboard, 'old_settings', raising=False)

    keyboard_mod.Keyboard.start()

    assert keyboard_mod.Keyboard.enabled is False
    assert not hasattr(keyboard_mod.Keyboard, 'old_settings')
    assert keyboard_mod.Keyboard.check_key() is None

    # Teardown must be just as tolerant: nothing was saved, so nothing is
    # restored and no exception escapes.
    keyboard_mod.Keyboard.stop()


@pytest.mark.skipif(os.name == 'nt', reason="termios is POSIX only")
def test_keyboard_start_setcbreak_failure_leaves_no_state(monkeypatch):
    """A probe that succeeds but a mode change that fails must not be recorded.

    Saving settings for a terminal we never reconfigured would have stop()
    push them back onto a terminal that never changed.
    """
    monkeypatch.setattr(keyboard_mod.termios, 'tcgetattr', lambda x: 'settings')
    monkeypatch.delattr(keyboard_mod.Keyboard, 'old_settings', raising=False)

    def fails(_):
        raise keyboard_mod.termios.error(25, 'Inappropriate ioctl for device')

    monkeypatch.setattr(keyboard_mod.tty, 'setcbreak', fails)
    monkeypatch.setattr(keyboard_mod.sys.stdin, 'fileno', lambda: 0)

    keyboard_mod.Keyboard.start()

    assert keyboard_mod.Keyboard.enabled is False
    assert not hasattr(keyboard_mod.Keyboard, 'old_settings')


@pytest.mark.skipif(os.name == 'nt', reason="termios is POSIX only")
def test_keyboard_stop_tolerates_terminal_going_away(monkeypatch):
    monkeypatch.setattr(keyboard_mod.termios, 'tcgetattr', lambda x: 'settings')
    monkeypatch.setattr(keyboard_mod.tty, 'setcbreak', lambda x: None)
    monkeypatch.setattr(keyboard_mod.sys.stdin, 'fileno', lambda: 0)
    keyboard_mod.Keyboard.start()
    assert keyboard_mod.Keyboard.enabled is True

    def gone(*args):
        raise keyboard_mod.termios.error(5, 'Input/output error')

    monkeypatch.setattr(keyboard_mod.termios, 'tcsetattr', gone)

    keyboard_mod.Keyboard.stop()

    assert keyboard_mod.Keyboard.enabled is False
    # The saved settings describe a terminal that no longer exists; a second
    # stop() must not retry them.
    assert not hasattr(keyboard_mod.Keyboard, 'old_settings')
    keyboard_mod.Keyboard.stop()


@pytest.mark.skipif(os.name == 'nt', reason="termios is POSIX only")
def test_keyboard_check_key_disables_on_terminal_loss(monkeypatch):
    keyboard_mod.Keyboard.enabled = True

    def gone(*args, **kwargs):
        raise OSError(9, 'Bad file descriptor')

    monkeypatch.setattr(keyboard_mod.select, 'select', gone)

    # A detached terminal must not throw out of the dashboard's render loop.
    assert keyboard_mod.Keyboard.check_key() is None
    assert keyboard_mod.Keyboard.enabled is False
