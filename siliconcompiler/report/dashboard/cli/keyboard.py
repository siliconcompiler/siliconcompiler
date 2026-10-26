import os

from typing import Optional


# Detect the operating system
if os.name == 'nt':
    # Windows setup
    import msvcrt

    #: Errors raised when the terminal cannot be probed or reconfigured.
    TERMINAL_ERRORS = (OSError, ValueError)

    def check_key(fd: Optional[int]) -> Optional[str]:
        # msvcrt reads the console itself, so there is no descriptor to poll.
        if msvcrt.kbhit():
            return msvcrt.getch().decode('utf-8', errors='ignore')
        return None
else:
    # macOS/Linux setup
    import tty
    import termios

    # ``termios.error`` is NOT a subclass of OSError -- its MRO is
    # (termios.error, Exception, BaseException, object) -- so both are caught:
    # termios calls fail with the former, opening and reading with the latter.
    TERMINAL_ERRORS = (OSError, termios.error)

    def check_key(fd: int) -> Optional[str]:
        try:
            return os.read(fd, 1).decode('utf-8', errors='ignore')
        except BlockingIOError:
            return None


class Keyboard:
    enabled: bool = False
    #: The controlling terminal, open from start() to stop().
    fd: Optional[int] = None

    @staticmethod
    def start() -> None:
        """
        Set up the terminal to read single key presses without blocking.

        Keys are read from the controlling terminal, not stdin: the process
        that draws the dashboard can be a ``ProcessPoolExecutor`` worker, which
        inherits the parent's terminal but is handed /dev/null on stdin.

        This is a no-op when there is no controlling terminal, or when this
        process is not in its foreground job. Keyboard input is a convenience,
        so a terminal that cannot be set up must degrade to "no hotkeys", never
        fail the run that opened the dashboard.
        """
        # Start from disabled, so a failed probe below leaves hotkeys off
        # rather than inheriting an "enabled" from an earlier terminal. Under
        # the fork start method a worker inherits this class attribute from its
        # parent.
        Keyboard.enabled = False

        if os.name == 'nt':
            return

        # Non-blocking applies to this open of the terminal only, not to the
        # stdin the shell shares.
        try:
            fd = os.open("/dev/tty", os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            return

        try:
            # Changing the mode from a background job would stop the whole job
            # with SIGTTOU.
            if os.tcgetpgrp(fd) == os.getpgrp():
                old_settings = termios.tcgetattr(fd)
                tty.setcbreak(fd)
                Keyboard.fd = fd
                Keyboard.old_settings = old_settings
                Keyboard.enabled = True
                return
        except TERMINAL_ERRORS:
            pass
        os.close(fd)

    @staticmethod
    def stop() -> None:
        """
        Restore the terminal settings to their original state.
        """
        Keyboard.enabled = False
        if os.name == 'nt':
            return

        old_settings = getattr(Keyboard, 'old_settings', None)
        if old_settings is None:
            return

        # Only start() sets old_settings, and only after a successful probe, so
        # a failure here means the terminal went away mid-run. Drop the saved
        # settings either way: they describe a terminal that no longer exists.
        del Keyboard.old_settings
        fd, Keyboard.fd = Keyboard.fd, None
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except TERMINAL_ERRORS:
            pass
        os.close(fd)

    @staticmethod
    def check_key() -> Optional[str]:
        """
        Check if a key has been pressed and return it.
        Returns None if no key is pressed.
        """
        if not Keyboard.enabled:
            return None
        try:
            return check_key(Keyboard.fd)
        except TERMINAL_ERRORS:
            # The terminal was detached mid-run. Stop polling rather than
            # letting this escape into the dashboard's render loop.
            Keyboard.enabled = False
            return None
