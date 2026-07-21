import logging
import re
import sys

from collections import deque

from siliconcompiler import utils


class SCHistoryLogHandler(logging.Handler):
    """
    Retains the most recent log records in a bounded in-memory ring buffer.

    Attached to the project logger for the lifetime of the project so a
    component that attaches late — notably the CLI dashboard's log pane — can
    be seeded with the history that preceded it, rather than starting blank.

    Raw :class:`logging.LogRecord` objects are stored (not formatted strings)
    so a late consumer can re-format them with whatever formatter it uses.
    """

    def __init__(self, capacity: int = 1000):
        super().__init__()
        self.__records = deque(maxlen=capacity)

    def emit(self, record):
        self.__records.append(record)

    @property
    def records(self):
        """List of retained records, oldest first."""
        return list(self.__records)

    def clear(self):
        """Drop all retained records.

        Called once a consumer (the dashboard log pane) has drained the
        history into its own buffer, so the same records are not handed out —
        and re-rendered — again on a later attach.
        """
        self.__records.clear()


class SCSuppressLoggerFilter(logging.Filter):
    """
    A togglable filter that suppresses every record while ``active`` is True.
    Used to silence an existing handler without detaching it (so external
    references to the handler stay valid) while another component owns the
    terminal — e.g. the CLI dashboard's live view.
    """

    def __init__(self):
        super().__init__()
        self.active = False

    def filter(self, record):
        return not self.active


class SCTeeLoggerHandler(logging.Handler):
    """
    Forwards each record to every handler currently attached to ``logger``,
    optionally skipping one (typically a handler the caller already dispatches
    to directly, to avoid double delivery).

    The handler list is resolved on every emit, so sinks added or removed
    after this handler was created take effect with no reconfiguration.
    Intended for the QueueListener path so child-process records reach
    handlers that were added to the logger after the listener was built.
    """

    def __init__(self, logger: logging.Logger, skip: logging.Handler = None):
        super().__init__()
        self._logger = logger
        self._skip = skip

    def emit(self, record):
        for handler in list(self._logger.handlers):
            if handler is self._skip or handler is self:
                # Skip the caller's own pipe handler (typically the one the
                # QueueListener already dispatches to) and the tee itself
                # (in case it ever gets attached to the logger it watches,
                # which would otherwise recurse infinitely).
                continue
            try:
                handler.handle(record)
            except Exception:
                # A failing downstream sink must not break delivery to the
                # other handlers in the caller's chain. We intentionally do
                # NOT call self.handleError(record) here: handleError writes
                # to sys.stderr, which bypasses the suppression filter the
                # dashboard installs and would corrupt the rich Live screen.
                pass


class SCBlankLoggerFormatter(logging.Formatter):
    def __init__(self):
        super().__init__("%(message)s")


class SCBlankColorlessLoggerFormatter(logging.Formatter):
    def __init__(self):
        super().__init__("%(message)s")

        self.__rm = re.compile(u"\u001b\\[(\\d+)m")

    def format(self, record):
        msg = super().format(record)

        return self.__rm.sub("", msg)


class SCDebugLoggerFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(
            "| %(levelname)-8s | %(filename)-20s : %(funcName)-10s | %(lineno)-4s | %(message)s")


class SCDebugInRunLoggerFormatter(logging.Formatter):
    def __init__(self, project, jobname, step, index):
        super().__init__(
            SCInRunLoggerFormatter.configure_format(
                "| %(levelname)-8s | %(filename)-20s : %(funcName)-10s | %(lineno)-4s |"
                " {} | {} | {} | %(message)s",
                project, step, index))


class SCLoggerFormatter(logging.Formatter):
    def __init__(self):
        super().__init__("| %(levelname)-8s | %(message)s")


class SCInRunLoggerFormatter(logging.Formatter):
    def __init__(self, project, jobname, step, index):
        super().__init__(
            SCInRunLoggerFormatter.configure_format(
                "| %(levelname)-8s | {} | {} | {} | %(message)s",
                project, step, index))

    @staticmethod
    def configure_format(fmt, project, step, index):
        from siliconcompiler.remote import client

        max_width = 20

        flow = project.option.get_flow()
        if flow:
            nodes_to_run = list(project.get_flow(flow).get_nodes())
        else:
            nodes_to_run = []

        # Figure out how wide to make step and index fields
        max_step_len = 1
        max_index_len = 1

        if project.option.get_remote():
            nodes_to_run.append((client.remote_step_name, '0'))
        for future_step, future_index in nodes_to_run:
            max_step_len = max(len(future_step), max_step_len)
            max_index_len = max(len(future_index), max_index_len)
        max_step_len = min(max_step_len, max_width)
        max_index_len = min(max_index_len, max_width)

        jobname = project.option.get_jobname()

        if step is None:
            step = '-' * max(max_step_len // 4, 1)
        if index is None:
            index = '-' * max(max_index_len // 4, 1)

        return fmt.format(
            utils.truncate_text(jobname, max_width),
            f'{utils.truncate_text(step, max_step_len): <{max_step_len}}',
            f'{utils.truncate_text(index, max_index_len): >{max_index_len}}')


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
    def supports_color(stream):
        supported_platform = sys.platform != 'win32'
        try:
            is_a_tty = hasattr(stream, 'isatty') and stream.isatty()
        except:  # noqa E722
            is_a_tty = False

        return supported_platform and is_a_tty


def get_console_formatter(project, in_run, step, index):
    if in_run:
        base_format = SCInRunLoggerFormatter(
            project,
            project.option.get_jobname(),
            step, index)
    else:
        base_format = SCLoggerFormatter()

    support_color = SCColorLoggerFormatter.supports_color(sys.stdout)
    if support_color:
        return SCColorLoggerFormatter(base_format)
    return base_format


def get_stream_handler(project, in_run, step, index):
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(get_console_formatter(project, in_run, step, index))
    return handler
