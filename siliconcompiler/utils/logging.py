import logging
import sys

from logging.handlers import QueueHandler, QueueListener

from siliconcompiler.flowgraph import _get_flowgraph_nodes
from siliconcompiler.remote import client
from siliconcompiler import utils


DEFAULT_FMT = "| %(levelname)-8s | %(message)s"
IN_RUN_FMT = "| %(levelname)-8s | %(jobname)-{}s | %(step)-{}s | %(index)-{}s | %(message)s"
DEBUG_FMT = "| %(levelname)-8s | %(filename)-20s : %(funcName)-10s | %(lineno)-4s | %(jobname)-{}s | %(step)-{}s | %(index)-{}s | %(message)s"
DEBUG_IN_RUN_FMT = "| %(levelname)-8s | %(filename)-20s : %(funcName)-10s | %(lineno)-4s | %(message)s"


class SCLoggerFormatter(logging.Formatter):
    def __init__(self, logger):
        self._logger = logger
        self._formatters = {
            None: {
                None: logging.Formatter(DEFAULT_FMT)
            },
            "debug": {
                None: logging.Formatter(DEBUG_IN_RUN_FMT)
            },
            "inrun": {
                None: logging.Formatter(DEFAULT_FMT)
            },
            "debug-inrun": {
                None: logging.Formatter(DEBUG_IN_RUN_FMT)
            }
        }

    def init_formatters(self):
        joblen, steplen, indexlen = self._logger.get_max_columns()

        self._formatters["inrun"][None] = logging.Formatter(
            IN_RUN_FMT.format(joblen, steplen, indexlen))
        self._formatters["debug-inrun"][None] = logging.Formatter(
            DEBUG_IN_RUN_FMT.format(joblen, steplen, indexlen))

    def format(self, record):
        if self._logger.getDebug():
            if self._logger.getInRun():
                formatters = self._formatters["debug-inrun"]
            else:
                formatters = self._formatters["debug"]
        else:
            if self._logger.getInRun():
                formatters = self._formatters["inrun"]
            else:
                formatters = self._formatters[None]

        log_fmt = formatters.get(record.levelno)
        if not log_fmt:
            log_fmt = formatters.get(None)

        return log_fmt.format(record)


class SCBlankLoggerFormatter(SCLoggerFormatter):
    def __init__(self, logger):
        super().__init__(logger)

        self._formatters = {}

        self.__format = logging.Formatter('%(message)s')

    def init_formatters(self):
        return

    def format(self, record):
        return self.__format.format(record)


class SCColorLoggerFormatter(SCLoggerFormatter):
    '''
    Apply color to stream logger
    '''
    blue = u"\u001b[34m"
    yellow = u"\u001b[33m"
    red = u"\u001b[31m"
    bold_red = u"\u001b[31;1m"
    reset = u"\u001b[0m"

    def __init__(self, logger):
        super().__init__(logger)

        self._formatters = {
            None: self.__create_color_format(DEFAULT_FMT),
            "debug": self.__create_color_format(DEBUG_IN_RUN_FMT),
            "inrun": self.__create_color_format(DEFAULT_FMT),
            "debug-inrun": self.__create_color_format(DEBUG_IN_RUN_FMT)
        }

    def init_formatters(self):
        joblen, steplen, indexlen = self._logger.get_max_columns()

        self._formatters["inrun"] = self.__create_color_format(
            IN_RUN_FMT.format(joblen, steplen, indexlen))
        self._formatters["debug-inrun"] = self.__create_color_format(
            DEBUG_IN_RUN_FMT.format(joblen, steplen, indexlen))

    def __create_color_format(self, fmt):
        formatters = {
            None: logging.Formatter(fmt)
        }

        for level, color in [(logging.DEBUG, SCColorLoggerFormatter.blue),
                             (logging.WARNING, SCColorLoggerFormatter.yellow),
                             (logging.ERROR, SCColorLoggerFormatter.red),
                             (logging.CRITICAL, SCColorLoggerFormatter.bold_red)]:
            formatters[level] = logging.Formatter(
                fmt.replace('%(levelname)-8s',
                            color + '%(levelname)-8s' + SCColorLoggerFormatter.reset))

        return formatters

    @staticmethod
    def supports_color(handler):
        if type(handler) is not logging.StreamHandler:
            return False

        supported_platform = sys.platform != 'win32'
        try:
            is_a_tty = hasattr(handler.stream, 'isatty') and handler.stream.isatty()
        except:  # noqa E722
            is_a_tty = False

        return supported_platform and is_a_tty


class SCLogger:
    def __init__(self, chip, max_column_width=20):
        # Create unique logger
        self._logger = logging.getLogger(f'sc_{id(chip)}')
        self._logger.propagate = False

        self.__chip = chip

        self._console = None
        self.__queued_listener = None

        self.__levelstack = []

        self.__max_column_width = max_column_width

        self.__support_color = SCColorLoggerFormatter.supports_color(logging.StreamHandler(stream=sys.stdout))

        self.initStdOut()

        # set a default log level
        self.setLevel(logging.INFO)

        self.setDebug(False)
        self.setInRun(False)

    def initStdOut(self, queue=None):
        if self._console:
            self._logger.removeHandler(self._console)

        if queue:
            self._console = QueueHandler(queue)
        else:
            self._console = logging.StreamHandler(stream=sys.stdout)

        self.__resetConsoleFormatter()

        self._logger.addHandler(self._console)
        self.set_max_columns()

    def __resetConsoleFormatter(self):
        if self.__support_color:
            self._console.setFormatter(SCColorLoggerFormatter(self))
        else:
            self._console.setFormatter(SCLoggerFormatter(self))

    def set_max_columns(self):
        # Figure out how wide to make step and index fields
        self.__max_jobname_len = self.__max_column_width // 4
        self.__max_step_len = self.__max_column_width // 4
        self.__max_index_len = self.__max_column_width // 4

        if not hasattr(self.__chip, 'schema'):
            # gate against chip creation ordering
            return

        self.__max_jobname_len = len(self.__chip.get('option', 'jobname'))

        if self.__chip.get('option', 'flow'):
            nodes_to_run = _get_flowgraph_nodes(self.__chip, flow=self.__chip.get('option', 'flow'))
        else:
            nodes_to_run = []

        self.__max_step_len = 1
        self.__max_index_len = 1

        if self.__chip.get('option', 'remote'):
            nodes_to_run.append((client.remote_step_name, '0'))
        for future_step, future_index in nodes_to_run:
            self.__max_step_len = max(len(future_step), self.__max_step_len)
            self.__max_index_len = max(len(future_index), self.__max_index_len)
        self.__max_step_len = min(self.__max_step_len, self.__max_column_width)
        self.__max_index_len = min(self.__max_index_len, self.__max_column_width)

        for handler in self._logger.handlers:
            if hasattr(handler.formatter, 'init_formatters'):
                handler.formatter.init_formatters()

    def get_max_columns(self):
        return self.__max_jobname_len, self.__max_step_len, self.__max_index_len

    def setInRun(self, value):
        self.__inrun = value

    def getInRun(self):
        return self.__inrun

    def setDebug(self, value):
        self.__debug = value

    def getDebug(self):
        return self.__debug

    def addFileHandler(self, path):
        handler = logging.FileHandler(path)
        handler.setFormatter(SCLoggerFormatter(self))
        self._logger.addHandler(handler)
        return handler

    def pushLogLevel(self, level):
        self.__levelstack.append(self._logger.level)
        self.setLevel(level)

    def popLogLevel(self):
        if self.__levelstack:
            self.setLevel(self.__levelstack.pop())

    def startQueuedListener(self, queue):
        self.__queued_listener = QueueListener(queue, self._console)
        self._console.setFormatter(SCBlankLoggerFormatter(self))

        self.__queued_listener.start()

    def stopQueuedListener(self):
        if self.__queued_listener:
            self.__queued_listener.stop()
            self.__queued_listener = None

            self.initStdOut()

    # Setup function forwarding
    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs, extra=self.__logger_args())

    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs, extra=self.__logger_args())

    def warning(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs, extra=self.__logger_args())

    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs, extra=self.__logger_args())

    def critical(self, msg, *args, **kwargs):
        self._logger.critical(msg, *args, **kwargs, extra=self.__logger_args())

    def log(self, level, msg, *args, **kwargs):
        self._logger.log(level, msg, *args, **kwargs, extra=self.__logger_args())

    def __logger_args(self):
        try:
            step = self.__chip.get("arg", "step")
            if step is None:
                step = '-' * max(self.__max_step_len // 4, 1)
            index = self.__chip.get("arg", "index")
            if index is None:
                index = '-' * max(self.__max_index_len // 4, 1)

            return {
                "jobname": utils.truncate_text(self.__chip.get("option", "jobname"),
                                               self.__max_jobname_len),
                "step": utils.truncate_text(step,
                                            self.__max_step_len),
                "index": utils.truncate_text(index,
                                             self.__max_index_len)
            }
        except:  # noqa E722
            return {
                "jobname": '-' * max(self.__max_jobname_len // 4, 1),
                "step": '-' * max(self.__max_step_len // 4, 1),
                "index": '-' * max(self.__max_index_len // 4, 1)
            }

    def setLevel(self, level):
        self._logger.setLevel(level)
        self.setDebug(level == logging.DEBUG)

    def getLevel(self):
        return self._logger.level

    def getChild(self, suffix):
        return self._logger.getChild(suffix)

    #######################################
    def __getstate__(self):
        # Called when generating a serial stream of the object
        attributes = self.__dict__.copy()

        # We have to remove the chip's logger before serializing the object
        # since the logger object is not serializable.
        del attributes['_logger']
        return attributes

    #######################################
    def __setstate__(self, state):
        self.__dict__ = state

        # Reinitialize logger on restore
        self._logger = logging.getLogger(f'sc_{id(self.__chip)}')
        self._logger.propagate = False
