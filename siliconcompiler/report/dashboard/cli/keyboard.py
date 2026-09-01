import os

from typing import Optional


# Detect the operating system
if os.name == 'nt':
    # Windows setup
    import msvcrt

    #: Errors raised when the terminal cannot be probed or reconfigured.
    TERMINAL_ERRORS = (OSError, ValueError)

    def check_key() -> Optional[str]:
        if msvcrt.kbhit():
            return msvcrt.getch().decode('utf-8', errors='ignore')
        return None
else:
    # macOS/Linux setup
    import sys
    import select
    import tty
    import termios

    # ``termios.error`` is NOT a subclass of OSError -- its MRO is
    # (termios.error, Exception, BaseException, object) -- so catching OSError
    # alone misses the single most common failure: a stdin that is not a
    # terminal, which raises termios.error(ENOTTY, "Inappropriate ioctl for
    # device"). Every process launched by multiprocessing gets /dev/null on
    # stdin, as does anything run under nohup, cron or a CI runner that closes
    # stdin, so this is the normal case for a worker, not an exotic one.
    # ValueError covers a stdin that has already been closed.
    TERMINAL_ERRORS = (OSError, termios.error, ValueError)

    def check_key() -> Optional[str]:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return None


class Keyboard:
    enabled: bool = False

    @staticmethod
    def start() -> None:
        """
        Set up the terminal to read single key presses without blocking.

        This is a no-op when stdin is not an interactive terminal. Keyboard
        input is a convenience -- the dashboard renders to stdout, which can
        be a terminal even when stdin is not (a ``ProcessPoolExecutor`` worker
        inherits the parent's stdout but is handed /dev/null on stdin) -- so a
        terminal that cannot be probed must degrade to "no hotkeys", never
        fail the run that opened the dashboard.
        """
        # Start from disabled, so a failed probe below leaves hotkeys off
        # rather than inheriting an "enabled" from an earlier terminal. This
        # matters across process boundaries: under the fork start method a
        # worker inherits this class attribute from a parent whose stdin was a
        # terminal, while its own is /dev/null -- polling that would spin on an
        # always-readable fd that only ever returns EOF.
        Keyboard.enabled = False

        if os.name == 'nt':
            return

        # Save the terminal settings for later restoration
        try:
            old_settings = termios.tcgetattr(sys.stdin)
        except TERMINAL_ERRORS:
            # stdin is not a terminal (or is gone), so it cannot be set up for
            # non-blocking input.
            return

        try:
            tty.setcbreak(sys.stdin.fileno())
        except TERMINAL_ERRORS:
            # tcgetattr succeeded but the mode change did not; leave the
            # terminal exactly as it was found rather than recording settings
            # that stop() would then try to restore.
            return

        Keyboard.old_settings = old_settings
        Keyboard.enabled = True

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
        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        except TERMINAL_ERRORS:
            pass

    @staticmethod
    def check_key() -> Optional[str]:
        """
        Check if a key has been pressed and return it.
        Returns None if no key is pressed.
        """
        if not Keyboard.enabled:
            return None
        try:
            return check_key()
        except TERMINAL_ERRORS:
            # The terminal was detached mid-run. Stop polling rather than
            # letting this escape into the dashboard's render loop.
            Keyboard.enabled = False
            return None
