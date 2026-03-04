import os

from typing import Optional


# Detect the operating system
if os.name == 'nt':
    # Windows setup
    import msvcrt

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
        """
        if os.name != 'nt':
            # Save the terminal settings for later restoration
            try:
                Keyboard.old_settings = termios.tcgetattr(sys.stdin)
            except OSError:
                # If stdin is not a terminal, we can't set it up for non-blocking input
                return
            Keyboard.enabled = True
            tty.setcbreak(sys.stdin.fileno())

    @staticmethod
    def stop() -> None:
        """
        Restore the terminal settings to their original state.
        """
        Keyboard.enabled = False
        if os.name != 'nt' and hasattr(Keyboard, 'old_settings'):
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, Keyboard.old_settings)

    @staticmethod
    def check_key() -> Optional[str]:
        """
        Check if a key has been pressed and return it.
        Returns None if no key is pressed.
        """
        if not Keyboard.enabled:
            return None
        return check_key()
