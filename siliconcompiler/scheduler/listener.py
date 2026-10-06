from typing import Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from siliconcompiler.project import Project


class RunListener:
    """Hears about runs as they happen.

    Register an instance with :meth:`~siliconcompiler.scheduler.Scheduler.add_listener`
    and it hears every run in the process. Each event is passed the project
    being run, and what happened is in that project's record and metrics, so a
    listener has no run state of its own to keep. Override the events you need;
    the rest do nothing.

    A run is told, in order: :meth:`run_started`; then, if setup succeeds,
    :meth:`flow_started`, :meth:`node_started` and :meth:`node_finished` for each
    node, and :meth:`flow_finished`; and last :meth:`run_finished`.

    Events are called on the thread running :meth:`~siliconcompiler.Project.run`,
    so a listener should return quickly: a slow one holds up the scheduling of
    every node. A listener that raises is logged and has no effect on the run
    or on the other listeners.
    """

    def run_started(self, project: "Project") -> None:
        """The run has begun and is about to check and set up its nodes. Which
        nodes will run is not known yet, and setup can still fail.

        Args:
            project (Project): The project being run.
        """

    def flow_started(self, project: "Project") -> None:
        """Setup is done and no node has been launched yet.

        Args:
            project (Project): The project being run.
        """

    def node_started(self, project: "Project", step: str, index: str) -> None:
        """A node was launched: its ``[record,status]`` is running and its
        ``[record,starttime]`` is set.

        Args:
            project (Project): The project being run.
            step (str): The node's step.
            index (str): The node's index.
        """

    def node_finished(self, project: "Project", step: str, index: str) -> None:
        """A node is over: its ``[record,status]`` is final, and its results are in
        the project if any arrived.

        Args:
            project (Project): The project being run.
            step (str): The node's step.
            index (str): The node's index.
        """

    def flow_finished(self, project: "Project", error: Optional[BaseException]) -> None:
        """No node is left running, and the run has been recorded in the project's
        history. Called for every run that called :meth:`flow_started`.

        Args:
            project (Project): The project being run.
            error (BaseException): What ended the flow, or None if it completed.
        """

    def run_finished(self, project: "Project", error: Optional[BaseException]) -> None:
        """The run is over. Called for every run that called :meth:`run_started`,
        including one that failed in setup.

        Args:
            project (Project): The project being run.
            error (BaseException): What ended the run, or None if it completed.
        """


class RunListeners(RunListener):
    """Passes each event on to a list of listeners, in order.

    A listener that raises is logged and skipped, so one broken listener can
    neither stop the run nor keep the others from hearing it. Interrupts and
    exits are not caught: they are how a run is stopped.
    """

    def __init__(self, listeners: Iterable[RunListener] = ()):
        self.__listeners = tuple(listeners)

    def __send(self, event: str, project: "Project", *args) -> None:
        for listener in self.__listeners:
            try:
                getattr(listener, event)(project, *args)
            except Exception as e:
                project.logger.error(f"{type(listener).__name__}.{event}() failed: {e}")
                project.logger.debug("Listener backtrace:", exc_info=True)

    def run_started(self, project: "Project") -> None:
        self.__send("run_started", project)

    def flow_started(self, project: "Project") -> None:
        self.__send("flow_started", project)

    def node_started(self, project: "Project", step: str, index: str) -> None:
        self.__send("node_started", project, step, index)

    def node_finished(self, project: "Project", step: str, index: str) -> None:
        self.__send("node_finished", project, step, index)

    def flow_finished(self, project: "Project", error: Optional[BaseException]) -> None:
        self.__send("flow_finished", project, error)

    def run_finished(self, project: "Project", error: Optional[BaseException]) -> None:
        self.__send("run_finished", project, error)
