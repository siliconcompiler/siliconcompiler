import os
import pytest
import select
import types

import siliconcompiler.report.dashboard.cli.keyboard as keyboard_mod


@pytest.fixture
def terminal(monkeypatch):
    """A pseudo-terminal standing in for the controlling terminal, with this process in its
    foreground job. Records the descriptors opened on it and closed.
    """
    term = types.SimpleNamespace(opened=[], closed=[])
    term.typed, term.fd = os.openpty()
    real_open, real_close = os.open, os.close

    def fake_open(path, flags, *args, **kwargs):
        if path != "/dev/tty":
            return real_open(path, flags, *args, **kwargs)
        fd = real_open(os.ttyname(term.fd), flags | os.O_NOCTTY)
        term.opened.append(fd)
        return fd

    def fake_close(fd):
        term.closed.append(fd)
        real_close(fd)

    monkeypatch.setattr(os, "open", fake_open)
    monkeypatch.setattr(os, "close", fake_close)
    monkeypatch.setattr(os, "tcgetpgrp", lambda fd: os.getpgrp())
    yield term
    keyboard_mod.Keyboard.stop()
    real_close(term.typed)
    real_close(term.fd)


def _cbreak(term):
    return not keyboard_mod.termios.tcgetattr(term.fd)[3] & keyboard_mod.termios.ICANON


@pytest.mark.skipif(os.name != 'nt', reason="msvcrt is Windows only")
@pytest.mark.parametrize("hit,key", [(False, None), (True, 'a')])
def test_check_key_windows(monkeypatch, hit, key):
    monkeypatch.setattr(keyboard_mod.msvcrt, 'kbhit', lambda: hit)
    monkeypatch.setattr(keyboard_mod.msvcrt, 'getch', lambda: b'a')
    assert keyboard_mod.check_key(None) == key


@pytest.mark.skipif(os.name != 'nt', reason="msvcrt is Windows only")
def test_keyboard_check_key_with_start_windows(monkeypatch):
    monkeypatch.setattr(keyboard_mod.Keyboard, 'enabled', True)
    monkeypatch.setattr(keyboard_mod.msvcrt, 'kbhit', lambda: True)
    monkeypatch.setattr(keyboard_mod.msvcrt, 'getch', lambda: b'x')
    assert keyboard_mod.Keyboard.check_key() == 'x'


def test_keyboard_check_key_without_start(monkeypatch):
    if os.name == 'nt':
        monkeypatch.setattr(keyboard_mod.msvcrt, 'kbhit', lambda: True)
        monkeypatch.setattr(keyboard_mod.msvcrt, 'getch', lambda: b'x')
    monkeypatch.setattr(keyboard_mod.Keyboard, 'enabled', False)
    assert keyboard_mod.Keyboard.check_key() is None


@pytest.mark.skipif(os.name == 'nt', reason="termios is POSIX only")
def test_keyboard_reads_controlling_terminal(terminal):
    """Keys come from the controlling terminal, not stdin, which a pool worker drawing a sweep's
    dashboard has as /dev/null.
    """
    keyboard_mod.Keyboard.start()
    assert keyboard_mod.Keyboard.enabled is True
    assert _cbreak(terminal)
    assert keyboard_mod.Keyboard.check_key() is None

    os.write(terminal.typed, b'h')
    select.select([terminal.fd], [], [], 5)
    assert keyboard_mod.Keyboard.check_key() == 'h'
    assert keyboard_mod.Keyboard.check_key() is None

    keyboard_mod.Keyboard.stop()
    assert not _cbreak(terminal)
    assert keyboard_mod.Keyboard.fd is None
    assert terminal.opened and set(terminal.opened) <= set(terminal.closed)


@pytest.mark.skipif(os.name == 'nt', reason="termios is POSIX only")
def test_keyboard_start_without_controlling_terminal(monkeypatch):
    """No controlling terminal, as under cron or a CI runner, disables hotkeys instead of
    failing the run.
    """
    real_open = os.open

    def no_tty(path, *args, **kwargs):
        if path == "/dev/tty":
            raise OSError(6, 'No such device or address')
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", no_tty)

    keyboard_mod.Keyboard.start()

    assert keyboard_mod.Keyboard.enabled is False
    assert keyboard_mod.Keyboard.fd is None
    assert keyboard_mod.Keyboard.check_key() is None
    keyboard_mod.Keyboard.stop()


@pytest.mark.skipif(os.name == 'nt', reason="termios is POSIX only")
def test_keyboard_start_in_background_job(terminal, monkeypatch):
    """A background job leaves the terminal alone: changing its mode would stop the job with
    SIGTTOU.
    """
    monkeypatch.setattr(os, "tcgetpgrp", lambda fd: os.getpgrp() + 1)

    keyboard_mod.Keyboard.start()

    assert keyboard_mod.Keyboard.enabled is False
    assert keyboard_mod.Keyboard.fd is None
    assert not _cbreak(terminal)
    assert terminal.opened and set(terminal.opened) <= set(terminal.closed)


@pytest.mark.skipif(os.name == 'nt', reason="termios is POSIX only")
def test_keyboard_start_setcbreak_failure_leaves_no_state(terminal, monkeypatch):
    """A failed setcbreak after a successful probe leaves no settings for stop() to restore."""
    def fails(_):
        raise keyboard_mod.termios.error(25, 'Inappropriate ioctl for device')

    monkeypatch.setattr(keyboard_mod.tty, 'setcbreak', fails)

    keyboard_mod.Keyboard.start()

    assert keyboard_mod.Keyboard.enabled is False
    assert keyboard_mod.Keyboard.fd is None
    assert not hasattr(keyboard_mod.Keyboard, 'old_settings')
    assert terminal.opened and set(terminal.opened) <= set(terminal.closed)


@pytest.mark.skipif(os.name == 'nt', reason="termios is POSIX only")
def test_keyboard_stop_tolerates_terminal_going_away(terminal, monkeypatch):
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
    assert keyboard_mod.Keyboard.fd is None
    assert set(terminal.opened) <= set(terminal.closed)
    keyboard_mod.Keyboard.stop()


@pytest.mark.skipif(os.name == 'nt', reason="termios is POSIX only")
def test_keyboard_check_key_disables_on_terminal_loss(monkeypatch):
    monkeypatch.setattr(keyboard_mod.Keyboard, 'enabled', True)

    def gone(fd):
        raise OSError(5, 'Input/output error')

    monkeypatch.setattr(keyboard_mod, 'check_key', gone)

    # A detached terminal must not throw out of the dashboard's render loop.
    assert keyboard_mod.Keyboard.check_key() is None
    assert keyboard_mod.Keyboard.enabled is False
