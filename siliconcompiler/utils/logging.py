import contextlib
import logging
import re
import sys

from collections import deque
from types import MappingProxyType

from siliconcompiler import utils


# Levels for output the *tool* produced, as opposed to SiliconCompiler's own
# reporting. Keeping them distinct lets a reader tell at a glance whether a
# line came from the tool's stdout/stderr or from SC itself -- which only
# became possible once the two streams stopped sharing a file description.
#
# Each sits one step above its nearest standard sibling so visibility is
# unchanged from when these were logged as INFO/ERROR: LOG appears wherever
# INFO does, LOGERROR wherever ERROR does. "LOGERROR" is exactly the eight
# characters the console formatter reserves for a level name.
SC_LOG = logging.INFO + 1
SC_LOGERROR = logging.ERROR + 1

logging.addLevelName(SC_LOG, "LOG")
logging.addLevelName(SC_LOGERROR, "LOGERROR")


# Attribute stamped on a LogRecord that was emitted while the console was muted
# by ['option', 'quiet']. Console sinks drop such a record; file sinks ignore
# the attribute entirely, so a quiet run's log files stay complete.
SC_CONSOLE_QUIET_ATTR = "sc_console_quiet"

# Attribute stamped on a LogRecord that must reach the screen even while the
# console is muted. Quiet exists to keep a chatty tool off the terminal, not to
# hide that the run is in trouble: a message about the health of the *run* --
# memory pressure, a timeout, a kill, a crash -- is exactly what a user who
# asked for quiet still needs to see, because the alternative is a job that
# appears to sit idle and then dies with no explanation on screen. Such a
# message opts out with::
#
#     logger.warning("...", extra=SC_CONSOLE_FORCE)
#
# Use it sparingly, and only for SiliconCompiler's own diagnostics: anything
# forced here is, by definition, something the user asked to suppress.
SC_CONSOLE_FORCE_ATTR = "sc_console_force"

# Read-only because logging copies an ``extra`` mapping's items onto every
# record it is handed to; a mutation here would leak into unrelated records.
SC_CONSOLE_FORCE = MappingProxyType({SC_CONSOLE_FORCE_ATTR: True})


class SCConsoleQuietFilter(logging.Filter):
    """
    Drops records tagged by :func:`console_quiet`.

    Attached to every sink that writes to the screen -- the project's terminal
    handler, the CLI dashboard's log pane, and the history buffer that seeds
    it -- so quiet only ever costs console visibility, never a log file.

    A record carrying :data:`SC_CONSOLE_FORCE` passes through regardless of the
    quiet tag; see that constant for what earns the exemption.
    """

    def filter(self, record):
        if getattr(record, SC_CONSOLE_FORCE_ATTR, False):
            return True
        return not getattr(record, SC_CONSOLE_QUIET_ATTR, False)


class _SCConsoleQuietTagger(logging.Filter):
    """
    Tags every record passing through it for console suppression.

    Installed on the *logger* rather than a handler so the tag is applied once,
    up front, and travels with the record to every sink -- including the
    QueueHandler that ships it to the parent process, which is where the
    console actually lives during a run.
    """

    def filter(self, record):
        setattr(record, SC_CONSOLE_QUIET_ATTR, True)
        return True


@contextlib.contextmanager
def console_quiet(logger: logging.Logger, active: bool = True):
    """
    Mutes the console for anything logged inside the block.

    Log files (the node log, job.log) still receive every record; only the
    screen is silenced. Used to make ['option', 'quiet'] apply to a task's own
    logging during pre_process()/run()/post_process(), which would otherwise
    bypass it entirely.

    A record logged with ``extra=SC_CONSOLE_FORCE`` still reaches the screen --
    see :data:`SC_CONSOLE_FORCE`.

    Args:
        logger (logging.Logger): The logger to mute.
        active (bool): When False the block runs unchanged, so callers can pass
            the quiet flag straight through instead of branching.
    """
    if not active:
        yield
        return

    tagger = _SCConsoleQuietTagger()
    logger.addFilter(tagger)
    try:
        yield
    finally:
        logger.removeFilter(tagger)


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
        # The history exists to feed the console (the dashboard log pane), so
        # it honors quiet exactly as the terminal handler does.
        self.addFilter(SCConsoleQuietFilter())

    def emit(self, record):
        self.__records.append(record)

    @property
    def records(self):
        """List of retained records, oldest first.

        Taken under the handler lock so the snapshot cannot race with a
        concurrent ``emit`` or ``clear``.
        """
        self.acquire()
        try:
            return list(self.__records)
        finally:
            self.release()

    def clear(self):
        """Drop all retained records.

        Called once a consumer (the dashboard log pane) has drained the
        history into its own buffer, so the same records are not handed out —
        and re-rendered — again on a later attach. Held under the handler lock
        so it cannot race with a concurrent ``emit``.
        """
        self.acquire()
        try:
            self.__records.clear()
        finally:
            self.release()

    def drain(self):
        """Atomically return all retained records and clear the buffer.

        The snapshot and the clear happen under the handler lock together, so
        a record emitted concurrently is either fully included in the returned
        list or retained for the next drain — never lost in a window between a
        separate ``records`` read and ``clear`` call.
        """
        self.acquire()
        try:
            records = list(self.__records)
            self.__records.clear()
            return records
        finally:
            self.release()


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

        # SC_LOG is left uncolored, like the INFO it stands in for.
        for level, color in [(logging.DEBUG, SCColorLoggerFormatter.blue),
                             (logging.WARNING, SCColorLoggerFormatter.yellow),
                             (logging.ERROR, SCColorLoggerFormatter.red),
                             (SC_LOGERROR, SCColorLoggerFormatter.red),
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
        except Exception:
            # The stream is whatever the caller handed us: a closed file raises
            # ValueError, a captured or wrapped stream can raise anything else.
            # Anything that cannot answer is treated as not a terminal.
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
    # This is the screen, so it is where ['option', 'quiet'] applies.
    handler.addFilter(SCConsoleQuietFilter())
    return handler
