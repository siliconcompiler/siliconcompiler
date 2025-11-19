import logging
import multiprocessing
import sys
import time

import os.path

from typing import List, Dict, Tuple, Optional, Callable, ClassVar, Any, Literal, TYPE_CHECKING

from logging.handlers import QueueListener

from siliconcompiler import NodeStatus
from siliconcompiler import utils
from siliconcompiler.flowgraph import RuntimeFlowgraph

from siliconcompiler.package import Resolver
from siliconcompiler.schema import Journal

from siliconcompiler.utils.logging import SCBlankLoggerFormatter, SCBlankColorlessLoggerFormatter
from siliconcompiler.utils.multiprocessing import MPManager
from siliconcompiler.scheduler import SCRuntimeError

if TYPE_CHECKING:
    from siliconcompiler import Flowgraph
    from siliconcompiler.project import Project
    from siliconcompiler.scheduler import SchedulerNode
    from siliconcompiler.schema_support.record import RecordSchema


class TaskScheduler:
    """A class for managing the execution of individual tasks in a flowgraph.

    This class is responsible for the fine-grained scheduling of tasks,
    handling multiprocessing, resource allocation (cores/threads), and
    dependency checking. It operates on a set of pending tasks defined by the
    main Scheduler and executes them in a loop until the flow is complete.
    """
    __callbacks: ClassVar[Dict[str, Callable[..., None]]] = {
        "pre_run": lambda project: None,
        "pre_node": lambda project, step, index: None,
        "post_node": lambda project, step, index: None,
        "post_run": lambda project: None,
    }

    @staticmethod
    def register_callback(hook: Literal["pre_run", "pre_node", "post_node", "post_run"],
                          func: Callable[..., None]) -> None:
        """Registers a callback function to be executed at a specific hook point.

        Valid hooks are 'pre_run', 'pre_node', 'post_node', and 'post_run'.

        Args:
            hook (str): The name of the hook to register the callback for.
            func (function): The function to be called. It should accept the
                project object and, for node hooks, the step and index as arguments.

        Raises:
            ValueError: If the specified hook is not valid.
        """
        if hook not in TaskScheduler.__callbacks:
            raise ValueError(f"{hook} is not a valid callback")
        TaskScheduler.__callbacks[hook] = func

    def __init__(self, project: "Project", tasks: Dict[Tuple[str, str], "SchedulerNode"]):
        """Initializes the TaskScheduler.

        Args:
            project (Project): The project object containing the configuration.
            tasks (dict): A dictionary of SchedulerNode objects keyed by
                (step, index) tuples.
        """
        self.__project = project
        self.__logger = self.__project.logger
        self.__logger_console_handler = self.__project._logger_console
        self.__schema = self.__project
        self.__flow: "Flowgraph" = self.__schema.get("flowgraph",
                                                     self.__project.get('option', 'flow'),
                                                     field="schema")
        self.__record: "RecordSchema" = self.__schema.get("record", field="schema")
        self.__dashboard = project._Project__dashboard

        self.__max_cores = utils.get_cores()
        self.__max_threads = utils.get_cores()
        self.__max_parallel_run = self.__project.option.scheduler.get_maxnodes()
        if not self.__max_parallel_run:
            self.__max_parallel_run = utils.get_cores()
        # clip max parallel jobs to 1 <= jobs <= max_cores
        self.__max_parallel_run = max(1, min(self.__max_parallel_run, self.__max_cores))

        self.__runtime_flow = RuntimeFlowgraph(
            self.__flow,
            from_steps=self.__project.option.get_from(),
            to_steps=self.__project.option.get_to(),
            prune_nodes=self.__project.option.get_prune())

        self.__log_queue = MPManager.get_manager().Queue()

        self.__nodes: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.__startTimes: Dict[Optional[Tuple[str, str]], float] = {}
        self.__dwellTime: float = 0.1

        self.__create_nodes(tasks)

    def __create_nodes(self, tasks: Dict[Tuple[str, str], "SchedulerNode"]) -> None:
        """
        Private helper to prepare all pending tasks for execution.

        This method iterates through the tasks identified by the main Scheduler,
        creates a multiprocessing.Process for each one, and sets up pipes for
        inter-process communication (primarily for logging and package resolution).

        Args:
            tasks (dict): A dictionary of SchedulerNode objects.
        """
        runtime = RuntimeFlowgraph(
            self.__flow,
            from_steps=set([step for step, _ in self.__flow.get_entry_nodes()]),
            prune_nodes=self.__project.option.get_prune())

        for step, index in self.__runtime_flow.get_nodes():
            if self.__record.get('status', step=step, index=index) != NodeStatus.PENDING:
                continue

            task = {
                "name": f"{step}/{index}",
                "inputs": runtime.get_node_inputs(step, index, record=self.__record),
                "proc": None,
                "parent_pipe": None,
                "threads": None,
                "running": False,
                "manifest": None,
                "node": tasks[(step, index)]
            }

            with tasks[(step, index)].runtime():
                threads = tasks[(step, index)].threads
                task["manifest"] = tasks[(step, index)].get_manifest()
            if not threads:
                threads = self.__max_threads
            task["threads"] = max(1, min(threads, self.__max_threads))

            task["parent_pipe"], pipe = multiprocessing.Pipe()
            task["node"].set_queue(pipe, self.__log_queue)

            task["proc"] = multiprocessing.Process(target=task["node"].run)
            self.__nodes[(step, index)] = task

        # Create ordered list of nodes
        self.__ordered_nodes: List[Tuple[str, str]] = []
        for levelnodes in self.__runtime_flow.get_execution_order():
            for node in levelnodes:
                if node in self.__nodes:
                    self.__ordered_nodes.append(node)

    def run(self, job_log_handler: logging.Handler) -> None:
        """
        The main entry point for the task scheduling loop.

        This method sets up a listener to handle logs from child processes,
        calls the 'pre_run' callback, enters the main execution loop, and
        handles cleanup and the 'post_run' callback.

        Args:
            job_log_handler (logging.FileHandler): The handler for the main job log file.
        """
        # Call this in case this was invoked without __main__
        multiprocessing.freeze_support()

        # Handle logs across threads
        log_listener = QueueListener(self.__log_queue, self.__logger_console_handler,
                                     job_log_handler)
        console_format = self.__logger_console_handler.formatter
        file_formatter = job_log_handler.formatter
        self.__logger_console_handler.setFormatter(SCBlankLoggerFormatter())
        job_log_handler.setFormatter(SCBlankColorlessLoggerFormatter())
        self.__logger.removeHandler(job_log_handler)

        log_listener.start()

        # Update dashboard before run begins
        if self.__dashboard:
            self.__dashboard.update_manifest()

        TaskScheduler.__callbacks["pre_run"](self.__project)

        try:
            self.__run_loop()
            TaskScheduler.__callbacks["post_run"](self.__project)
        except KeyboardInterrupt:
            # exit immediately
            log_listener.stop()
            sys.exit(0)
        finally:
            # Cleanup logger
            try:
                log_listener.stop()
            except AttributeError:
                # Logger already stopped
                pass
            self.__logger_console_handler.setFormatter(console_format)
            job_log_handler.setFormatter(file_formatter)
            self.__logger.addHandler(job_log_handler)

    def __run_loop(self) -> None:
        """
        The core execution loop of the scheduler.

        This loop continues as long as there are nodes running or waiting to
        run. In each iteration, it processes completed nodes and launches new
        ones whose dependencies have been met.
        """
        self.__startTimes = {None: time.time()}

        while len(self.get_nodes_waiting_to_run()) > 0 or len(self.get_running_nodes()) > 0:
            changed = self.__process_completed_nodes()
            changed |= self.__launch_nodes()

            if changed and self.__dashboard:
                # Update dashboard if the manifest changed
                self.__dashboard.update_manifest(payload={"starttimes": self.__startTimes})

            running_nodes = self.get_running_nodes()

            # Check for situation where we have stuff left to run but don't
            # have any nodes running. This can happen when the flow generated an error
            if len(self.get_nodes_waiting_to_run()) > 0 and len(running_nodes) == 0:
                # Stop execution loop and report error
                break

            if len(running_nodes) == 1:
                # if there is only one node running, just join the thread
                self.__nodes[running_nodes[0]]["proc"].join()
            elif len(running_nodes) > 1:
                # if there are more than 1, join the first with a timeout
                self.__nodes[running_nodes[0]]["proc"].join(timeout=self.__dwellTime)

    def get_nodes(self) -> List[Tuple[str, str]]:
        """Gets an ordered list of all nodes managed by this scheduler.

        Returns:
            list: A list of (step, index) tuples for all nodes.
        """
        return self.__ordered_nodes

    def get_running_nodes(self) -> List[Tuple[str, str]]:
        """Gets an ordered list of all nodes that are currently running.

        Returns:
            list: A list of (step, index) tuples for running nodes.
        """
        nodes = []
        for node in self.get_nodes():
            info = self.__nodes[node]
            if info["running"]:
                nodes.append(node)
        return nodes

    def get_nodes_waiting_to_run(self) -> List[Tuple[str, str]]:
        """Gets an ordered list of all nodes that are pending execution.

        Returns:
            list: A list of (step, index) tuples for pending nodes.
        """
        nodes = []
        for node in self.get_nodes():
            info = self.__nodes[node]
            if not info["running"] and info["proc"]:
                nodes.append(node)
        return nodes

    def __process_completed_nodes(self) -> bool:
        """
        Private helper to check for and process completed nodes.

        This method iterates through running nodes, checks if their process has
        terminated, and if so, merges their results (manifest and package cache)
        back into the main project object. It updates the node's status based on
        the process exit code.

        Returns:
            bool: True if any node's status changed, False otherwise.
        """
        changed = False
        for node in self.get_running_nodes():
            info = self.__nodes[node]

            if not info["proc"].is_alive():
                manifest = info["manifest"]

                self.__logger.debug(f'{info["name"]} is complete merging: {manifest}')

                if os.path.exists(manifest):
                    Journal.replay_file(self.__schema, manifest)
                    # TODO: once tool is fixed this can go away
                    self.__schema.unset("arg", "step")
                    self.__schema.unset("arg", "index")

                if info["parent_pipe"] and info["parent_pipe"].poll(1):
                    try:
                        packages = info["parent_pipe"].recv()
                        if isinstance(packages, dict):
                            for package, path in packages.items():
                                Resolver.set_cache(self.__project, package, path)
                    except:  # noqa E722
                        pass

                step, index = node
                if info["proc"].exitcode > 0:
                    status = NodeStatus.ERROR
                else:
                    status = self.__record.get('status', step=step, index=index)
                    if not status or status == NodeStatus.PENDING:
                        status = NodeStatus.ERROR

                self.__record.set('status', status, step=step, index=index)

                info["running"] = False
                info["proc"] = None

                changed = True

                TaskScheduler.__callbacks['post_node'](self.__project, step, index)

        return changed

    def __allow_start(self, node: Tuple[str, str]) -> bool:
        """
        Private helper to check if a node is allowed to start based on resources.

        This method checks if launching a new node would exceed the configured
        maximum number of parallel jobs or the total available CPU cores.

        Args:
            node (tuple): The (step, index) of the node to check.

        Returns:
            bool: True if the node can be launched, False otherwise.
        """
        info = self.__nodes[node]

        if not info["node"].is_local:
            # using a different scheduler, so allow
            return True

        running_nodes = self.get_running_nodes()

        if len(running_nodes) >= self.__max_parallel_run:
            # exceeding machine resources
            return False

        current_threads = sum([self.__nodes[run_node]["threads"] for run_node in running_nodes])

        if info["threads"] + current_threads > self.__max_cores:
            # delay until there are enough core available
            return False

        # allow
        return True

    def __launch_nodes(self) -> bool:
        """
        Private helper to launch new nodes whose dependencies are met.

        This method iterates through pending nodes, checks if all their input
        nodes have completed successfully, and if system resources are available.
        If all conditions are met, it starts the node's process.

        Returns:
            bool: True if any new node was launched, False otherwise.
        """
        changed = False
        for node in self.get_nodes_waiting_to_run():
            # TODO: breakpoint logic:
            # if node is breakpoint, then don't launch while len(running_nodes) > 0

            info = self.__nodes[node]
            step, index = node

            ready = True
            inputs = []
            able_to_run = True
            for in_step, in_index in info["inputs"]:
                in_status = self.__record.get('status', step=in_step, index=in_index)
                inputs.append(in_status)

                if not NodeStatus.is_done(in_status):
                    ready = False
                if NodeStatus.is_error(in_status) and not info["node"].is_builtin:
                    # Fail if any dependency failed for non-builtin task
                    able_to_run = False

            # Fail if no dependency successfully finished for builtin task
            if inputs:
                any_success = any([status == NodeStatus.SUCCESS for status in inputs])
            else:
                any_success = True
            if ready and info["node"].is_builtin and not any_success:
                able_to_run = False

            if not able_to_run:
                info["proc"] = None
                continue

            # If there are no dependencies left, launch this node and
            # remove from nodes_to_run.
            if ready and self.__allow_start(node):
                self.__logger.debug(f'Launching {info["name"]}')

                TaskScheduler.__callbacks['pre_node'](self.__project, step, index)

                self.__record.set('status', NodeStatus.RUNNING, step=step, index=index)
                self.__startTimes[node] = time.time()
                changed = True

                # Start the process
                info["running"] = True
                info["proc"].start()

        return changed

    def check(self) -> None:
        """
        Checks if the flow completed successfully.

        This method verifies that all nodes designated as exit points in the
        flowgraph have been successfully completed.

        Raises:
            SCRuntimeError: If any final steps in the flow were not reached.
        """
        exit_steps = set([step for step, _ in self.__runtime_flow.get_exit_nodes()])
        completed_steps = set([step for step, _ in
                               self.__runtime_flow.get_completed_nodes(record=self.__record)])

        unreached = set(exit_steps).difference(completed_steps)

        if unreached:
            errors = set([f"{step}/{index}" for step, index in self.__runtime_flow.get_nodes()
                          if NodeStatus.is_error(self.__record.get("status",
                                                                   step=step, index=index))])
            if errors:
                raise SCRuntimeError(
                    f'Could not run final steps ({", ".join(sorted(unreached))}) '
                    f'due to errors in: {", ".join(sorted(errors))}')
            else:
                raise SCRuntimeError(f'Could not run final steps: {", ".join(sorted(unreached))}')
