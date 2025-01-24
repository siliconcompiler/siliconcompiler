import logging
import sys


class LoggerFormatter(logging.Formatter):
    def __init__(self, log_formatprefix, level_fmt, message_fmt):
        self.__formats = {}

        self.add_format(None, log_formatprefix + level_fmt, message_fmt)
        for level in [logging.DEBUG,
                      logging.INFO,
                      logging.WARNING,
                      logging.ERROR,
                      logging.CRITICAL]:
            self.add_format(level, log_formatprefix + level_fmt, message_fmt)

    def format(self, record):
        log_fmt = self.__formats.get(record.levelno)
        if not log_fmt:
            log_fmt = self.__formats.get(None)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

    def add_format(self, level, level_format, message_format):
        if level == logging.CRITICAL:
            self.__formats[level] = level_format + message_format
        else:
            self.__formats[level] = level_format + " " + message_format


class ColorStreamFormatter(LoggerFormatter):
    '''
    Apply color to stream logger
    '''
    blue = u"\u001b[34m"
    yellow = u"\u001b[33m"
    red = u"\u001b[31m"
    bold_red = u"\u001b[31;1m"
    reset = u"\u001b[0m"

    def __init__(self, log_formatprefix, level_fmt, message_fmt):
        super().__init__(log_formatprefix, level_fmt, message_fmt)

        # Replace with colors
        for level, color in [(logging.DEBUG, ColorStreamFormatter.blue),
                             (logging.WARNING, ColorStreamFormatter.yellow),
                             (logging.ERROR, ColorStreamFormatter.red),
                             (logging.CRITICAL, ColorStreamFormatter.bold_red)]:
            if color:
                fmt = log_formatprefix + color + level_fmt + ColorStreamFormatter.reset
            else:
                fmt = log_formatprefix + level_fmt

            self.add_format(level, fmt, message_fmt)

    @staticmethod
    def supports_color(handler):
        if not isinstance(handler, logging.StreamHandler):
            return False

        supported_platform = sys.platform != 'win32'
        try:
            is_a_tty = hasattr(handler.stream, 'isatty') and handler.stream.isatty()
        except:  # noqa E722
            is_a_tty = False

        return supported_platform and is_a_tty
