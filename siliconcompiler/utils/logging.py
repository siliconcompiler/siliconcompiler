import logging
import sys
from siliconcompiler.remote import client
from siliconcompiler import utils


class SCBlankLoggerFormatter(logging.Formatter):
    def __init__(self):
        super().__init__("%(message)s")


class SCDebugLoggerFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(
            "| %(levelname)-8s | %(filename)-20s : %(funcName)-10s | %(lineno)-4s | %(message)s")


class SCDebugInRunLoggerFormatter(logging.Formatter):
    def __init__(self, chip, jobname, step, index):
        super().__init__(
            SCInRunLoggerFormatter.configureFormat(
                "| %(levelname)-8s | %(filename)-20s : %(funcName)-10s | %(lineno)-4s |"
                " {} | {} | {} | %(message)s",
                chip, step, index))


class SCLoggerFormatter(logging.Formatter):
    def __init__(self):
        super().__init__("| %(levelname)-8s | %(message)s")


class SCInRunLoggerFormatter(logging.Formatter):
    def __init__(self, chip, jobname, step, index):
        super().__init__(
            SCInRunLoggerFormatter.configure_format(
                "| %(levelname)-8s | {} | {} | {} | %(message)s",
                chip, step, index))

    @staticmethod
    def configure_format(fmt, chip, step, index):
        max_width = 20

        flow = chip.get('option', 'flow')
        if flow:
            nodes_to_run = list(chip.schema.get("flowgraph", flow, field="schema").get_nodes())
        else:
            nodes_to_run = []

        # Figure out how wide to make step and index fields
        max_step_len = 1
        max_index_len = 1

        if chip.get('option', 'remote'):
            nodes_to_run.append((client.remote_step_name, '0'))
        for future_step, future_index in nodes_to_run:
            max_step_len = max(len(future_step), max_step_len)
            max_index_len = max(len(future_index), max_index_len)
        max_step_len = min(max_step_len, max_width)
        max_index_len = min(max_index_len, max_width)

        jobname = chip.get('option', 'jobname')

        if step is None:
            step = '-' * max(max_step_len // 4, 1)
        if index is None:
            index = '-' * max(max_index_len // 4, 1)

        return fmt.format(
            utils.truncate_text(jobname, max_width),
            f'{utils.truncate_text(step, max_step_len): <{max_step_len}}',
            f'{utils.truncate_text(index, max_step_len): >{max_index_len}}')


class SCColorLoggerFormatter(logging.Formatter):
    '''
    Apply color to stream logger
    '''
    blue = u"\u001b[34m"
    yellow = u"\u001b[33m"
    red = u"\u001b[31m"
    bold_red = u"\u001b[31;1m"
    reset = u"\u001b[0m"

    def __init__(self, root_formatter):
        super().__init__()

        self.__create_color_format(root_formatter._style._fmt)

    def __create_color_format(self, fmt):
        self.__formatters = {
            None: logging.Formatter(fmt)
        }

        for level, color in [(logging.DEBUG, SCColorLoggerFormatter.blue),
                             (logging.WARNING, SCColorLoggerFormatter.yellow),
                             (logging.ERROR, SCColorLoggerFormatter.red),
                             (logging.CRITICAL, SCColorLoggerFormatter.bold_red)]:
            self.__formatters[level] = logging.Formatter(
                fmt.replace('%(levelname)-8s',
                            color + '%(levelname)-8s' + SCColorLoggerFormatter.reset))

    def format(self, record):
        log_fmt = self.__formatters.get(record.levelno)
        if not log_fmt:
            log_fmt = self.__formatters.get(None)

        return log_fmt.format(record)

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
