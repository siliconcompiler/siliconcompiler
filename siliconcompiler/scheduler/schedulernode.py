import contextlib
import glob
import logging
import os
import shutil
import sys
import tarfile
import time

import os.path

from siliconcompiler.utils.multiprocessing import MPQueueHandler as QueueHandler

from typing import List, Optional, Set, Tuple, TYPE_CHECKING

from siliconcompiler import utils, sc_open
from siliconcompiler import NodeStatus
from siliconcompiler.utils.logging import get_console_formatter, SCInRunLoggerFormatter

from siliconcompiler.package import Resolver
from siliconcompiler.schema_support.record import RecordTime, RecordTool
from siliconcompiler.schema import Journal, Parameter
from siliconcompiler.scheduler import send_messages
from siliconcompiler.utils.paths import workdir, jobdir, collectiondir, cwdir

if TYPE_CHECKING:
    from siliconcompiler.project import Project
    from siliconcompiler import Flowgraph, Task
    from siliconcompiler.schema_support.record import RecordSchema
    from siliconcompiler.schema_support.metric import MetricSchema


class _SchedulerReset(Exception):
    def __init__(self, msg: str, *args: object) -> None:
        super().__init__(msg, *args)
        self.__msg = msg

    @property
    def msg(self) -> str:
        return self.__msg

    def log(self, logger: logging.Logger) -> None:
        logger.debug(self.msg)


class SchedulerFlowReset(_SchedulerReset):
    pass


class SchedulerNodeReset(_SchedulerReset):
    def log(self, logger: logging.Logger) -> None:
        logger.warning(self.msg)


class SchedulerNodeResetSilent(SchedulerNodeReset):
    def __init__(self, msg: str, *args: object) -> None:
        super().__init__(msg, *args)

    def log(self, logger: logging.Logger) -> None:
        _SchedulerReset.log(self, logger)


class SchedulerNode:
    """
    A class for managing and executing a single node in the compilation flow graph.

    This class encapsulates the state and logic required to run a specific
    step and index, including setting up directories, handling file I/O,
    executing the associated tool, and recording results.
    """

    __MAX_LOG_PRINT = 100  # Maximum number of warnings/error to print to log

    def __init__(self, project: "Project", step: str, index: str, replay: bool = False):
        """
        Initializes a SchedulerNode.

        Args:
            project (Project): The parent Project object containing the schema and settings.
            step (str): The step name in the flowgraph this node represents.
            index (str): The index for the step this node represents.
            replay (bool): If True, sets up the node to replay a previous run.

        Raises:
            TypeError: If 'step' or 'index' are not non-empty strings.
        """
        if not isinstance(step, str) or step == "":
            raise TypeError("step must be a string with a value")
        if not isinstance(index, str) or index == "":
            raise TypeError("index must be a string with a value")

        self.__step = step
        self.__index = index
        self.__project = project

        self.__name = self.__project.name
        self.__topmodule: str = self.__project.get(
            "library",
            self.__name,
            "fileset",
            self.__project.get("option", "fileset")[0],
            "topmodule")

        self.__record_user_info: bool = self.__project.get(
            "option", "track", step=self.__step, index=self.__index)
        self.__pipe = None
        self.__failed_log_lines = 20
        self.__error = False
        self.__generate_test_case = not replay
        self.__replay = replay
        self.__hash = self.__project.get("option", "hash")
        self.__breakpoint = self.__project.get("option", "breakpoint",
                                               step=self.__step, index=self.__index)
        self.__builtin = False

        self.__enforce_inputfiles = True
        self.__enforce_outputfiles = True

        self._update_job()

        flow: str = self.__project.get('option', 'flow')
        self.__is_entry_node: bool = (self.__step, self.__index) in \
            self.__project.get("flowgraph", flow, field="schema").get_entry_nodes()

        self.set_queue(None, None)
        self.__setup_schema_access()

    @contextlib.contextmanager
    def runtime(self):
        """
        A context manager to temporarily switch the node's active task.

        This is used to ensure that API calls within a specific context
        are directed to the correct task's schema.
        """
        prev_task = self.__task
        try:
            with self.__task.runtime(self) as runtask:
                self.__task = runtask
                yield
        finally:
            self.__task = prev_task

    @staticmethod
    def init(project: "Project") -> None:
        """Static placeholder for future initialization logic."""
        pass

    def switch_node(self, step: str, index: str) -> "SchedulerNode":
        """
        Creates a new SchedulerNode for a different step/index.

        This allows for context switching to inspect or interact with other nodes
        within the same project context.

        Args:
            step (str): The step name of the new node.
            index (str): The index of the new node.

        Returns:
            SchedulerNode: A new SchedulerNode instance for the specified step and index.
        """
        return SchedulerNode(self.__project, step, index)

    @property
    def is_local(self) -> bool:
        """bool: Returns True, indicating the node runs on the local machine."""
        return True

    @property
    def has_error(self) -> bool:
        """bool: True if the node has encountered an error."""
        return self.__error

    def set_builtin(self) -> None:
        """Flags this node as a 'builtin' node."""
        self.__builtin = True

    @property
    def is_builtin(self) -> bool:
        """bool: True if this node is a 'builtin' node."""
        return self.__builtin

    @property
    def logger(self) -> logging.Logger:
        """logging.Logger: The logger instance for this node."""
        return self.project.logger

    @property
    def project(self) -> "Project":
        """Project: The parent Project object."""
        return self.__project

    @property
    def step(self) -> str:
        """str: The step name of this node."""
        return self.__step

    @property
    def index(self) -> str:
        """str: The index of this node."""
        return self.__index

    @property
    def name(self) -> str:
        """str: The design name associated with this node."""
        return self.__name

    @property
    def topmodule(self) -> str:
        """str: The top module for this specific node."""
        return self.__topmodule

    @property
    def jobname(self) -> str:
        """str: The name of the current job."""
        return self.__job

    @property
    def project_cwd(self) -> str:
        """str: The original current working directory where the process was launched."""
        return self.__cwd

    @property
    def workdir(self) -> str:
        """str: The working directory for this specific node (step/index)."""
        return self.__workdir

    @property
    def jobworkdir(self) -> str:
        """str: The top-level working directory for the job."""
        return self.__jobworkdir

    @property
    def collection_dir(self) -> str:
        """str: The directory for collected source files."""
        return self.__collection_path

    @property
    def is_replay(self) -> bool:
        """bool: True if this node is configured for a replay run."""
        return self.__replay

    @property
    def task(self) -> "Task":
        """Task: The task object associated with this node."""
        return self.__task

    def _update_job(self):
        self.__job: str = self.__project.get('option', 'jobname')
        self.__cwd = cwdir(self.__project)
        self.__jobworkdir = jobdir(self.__project)
        self.__workdir = workdir(self.__project, step=self.__step, index=self.__index)
        self.__manifests = {
            "input": os.path.join(self.__workdir, "inputs", f"{self.__name}.pkg.json"),
            "output": os.path.join(self.__workdir, "outputs", f"{self.__name}.pkg.json")
        }
        self.__logs = {
            "sc": os.path.join(self.__workdir, f"sc_{self.__step}_{self.__index}.log"),
            "exe": os.path.join(self.__workdir, f"{self.__step}.log")
        }
        self.__replay_script = os.path.join(self.__workdir, "replay.sh")
        self.__collection_path = collectiondir(self.__project)

    def get_manifest(self, input: bool = False) -> str:
        """
        Gets the path to the input or output manifest file for this node.

        Args:
            input (bool): If True, returns the input manifest path. Otherwise,
                returns the output manifest path.

        Returns:
            str: The absolute path to the manifest file.
        """
        if input:
            return self.__manifests["input"]
        return self.__manifests["output"]

    def get_log(self, type: str = "exe") -> str:
        """
        Gets the path to a specific log file for this node.

        Args:
            type (str): The type of log file to retrieve ('exe' or 'sc').

        Returns:
            str: The absolute path to the log file.

        Raises:
            ValueError: If an unknown log type is requested.
        """
        if type not in self.__logs:
            raise ValueError(f"{type} is not a log")
        return self.__logs[type]

    @property
    def replay_script(self) -> str:
        """str: The path to the shell script for replaying this node's execution."""
        return self.__replay_script

    @property
    def threads(self) -> int:
        """int: The number of threads allocated for this node's task."""
        with self.__task.runtime(self) as task:
            thread_count = task.get("threads")
        return thread_count

    def set_queue(self, pipe, queue) -> None:
        """
        Configures the multiprocessing queue and pipe for inter-process communication.

        This is primarily used for logging from a child process back to the parent.

        Args:
            pipe: The pipe for sending data back to the parent process.
            queue: The multiprocessing.Queue for handling log records.
        """
        self.__pipe = pipe
        self.__queue = queue

        # Reinit
        self.__setup_schema_access()

    def __setup_schema_access(self) -> None:
        """
        Private helper to set up direct access to schema objects.

        This method initializes direct references to the schema objects for the
        flow, task, records, and metrics associated with this node, optimizing
        access to configuration and results.
        """
        flow = self.__project.get('option', 'flow')
        self.__flow: "Flowgraph" = self.__project.get("flowgraph", flow, field="schema")

        tool = self.__flow.get(self.__step, self.__index, 'tool')
        task = self.__flow.get(self.__step, self.__index, 'task')
        self.__task: "Task" = self.__project.get("tool", tool, "task", task, field="schema")
        self.__record: "RecordSchema" = self.__project.get("record", field="schema")
        self.__metrics: "MetricSchema" = self.__project.get("metric", field="schema")

    def _init_run_logger(self) -> None:
        """
        Initializes and configures the logger for the node's execution.

        This sets up the console formatter to include the step/index and redirects
        log output to a queue if one is provided for multiprocessing.
        """
        self.__project._logger_console.setFormatter(
            get_console_formatter(self.__project, True, self.__step, self.__index))

        if self.__queue:
            formatter = self.__project._logger_console.formatter
            self.logger.removeHandler(self.__project._logger_console)
            self.__project._logger_console = QueueHandler(self.__queue)
            self.__project._logger_console.setFormatter(formatter)
            self.logger.addHandler(self.__project._logger_console)

    def halt(self, msg: Optional[str] = None) -> None:
        """
        Stops the node's execution due to an error.

        This method logs an error message, sets the node's status to ERROR,
        writes the final manifest, and exits the process.

        Args:
            msg (str, optional): An error message to log.
        """
        if msg:
            self.logger.error(msg)

        self.__record.set("status", NodeStatus.ERROR, step=self.__step, index=self.__index)
        try:
            self.__project.write_manifest(self.__manifests["output"])
        except FileNotFoundError:
            self.logger.error(f"Failed to write manifest for {self.__step}/{self.__index}.")

        self.logger.error(f"Halting {self.__step}/{self.__index} due to errors.")
        send_messages.send(self.__project, "fail", self.__step, self.__index)
        sys.exit(1)

    def setup(self) -> bool:
        """
        Runs the setup() method for the node's assigned task.

        This method prepares the task for execution. If the task's setup()
        raises a TaskSkip exception, the node is marked as SKIPPED.

        Returns:
            bool: False if the node was skipped, True otherwise.

        Raises:
            Exception: Propagates any exception from the task's setup() method.
        """
        from siliconcompiler import TaskSkip

        with self.__task.runtime(self) as task:
            # Run node setup.
            self.logger.info(f'Setting up node {self.__step}/{self.__index} with '
                             f'{task.tool()}/{task.task()}')
            try:
                ret = task.setup()
                if ret is not None:
                    raise RuntimeError(f"setup() returned a value, but should not have: {ret}")
            except TaskSkip as skip:
                self.logger.warning(f'Removing {self.__step}/{self.__index} due to {skip.why}')
                self.__record.set('status', NodeStatus.SKIPPED,
                                  step=self.__step, index=self.__index)
                return False
            except Exception as e:
                self.logger.error(f'Failed to run setup() for {self.__step}/{self.__index} '
                                  f'with {task.tool()}/{task.task()}')
                raise e

            return True

    def check_previous_run_status(self, previous_run: "SchedulerNode") -> None:
        """
        Determine whether a prior run is compatible and completed successfully for use as
        an incremental build starting point.

        Performs compatibility checks (flow name, tool/task identity, completion status,
        and input-node set) against the provided previous run.

        Args:
            previous_run (SchedulerNode): Node object loaded from a previous run's manifest
                                          to compare against.

        Returns:
            `True` if the previous run completed and is compatible, `False` otherwise.

        Raises:
            SchedulerFlowReset: If the flow name differs and a full reset is required.
        """
        # Assume modified if flow does not match
        if self.__flow.name != previous_run.__flow.name:
            raise SchedulerFlowReset("Flow name changed, require full reset")

        # Tool name
        if self.__task.tool() != previous_run.__task.tool():
            raise SchedulerNodeResetSilent("Tool name changed")

        # Task name
        if self.__task.task() != previous_run.__task.task():
            raise SchedulerNodeResetSilent("Task name changed")

        previous_status = previous_run.__project.get("record", "status",
                                                     step=self.__step, index=self.__index)
        if not NodeStatus.is_done(previous_status):
            raise SchedulerNodeResetSilent("Previous step did not complete")

        if not NodeStatus.is_success(previous_status):
            raise SchedulerNodeResetSilent("Previous step was not successful")

        # Check input nodes
        log_level = self.logger.level
        self.logger.setLevel(logging.CRITICAL)
        sel_inputs = self.__task.select_input_nodes()
        self.logger.setLevel(log_level)
        if set(previous_run.__project.get("record", "inputnode",
                                          step=self.__step, index=self.__index)) != set(sel_inputs):
            raise SchedulerNodeReset(f'inputs to {self.__step}/{self.__index} has been '
                                     'modified from previous run')

    def check_values_changed(self, previous_run: "SchedulerNode", keys: Set[Tuple[str, ...]]) \
            -> None:
        """
        Checks if any specified schema parameter values have changed.

        Args:
            previous_run (SchedulerNode): The node object from a previous run.
            keys (set of tuples): A set of keypaths to check for changes.

        Returns:
            bool: True if any value has changed, False otherwise.
        """
        def gen_reset(key):
            raise SchedulerNodeReset(f'[{",".join(key)}] in {self.__step}/{self.__index} has been '
                                     'modified from previous run')

        for key in sorted(keys):
            if not self.__project.valid(*key) or not previous_run.__project.valid(*key):
                # Key is missing in either run
                gen_reset(key)

            param = self.__project.get(*key, field=None)
            step, index = self.__step, self.__index
            if param.get(field='pernode').is_never():
                step, index = None, None

            check_val = param.get(step=step, index=index)
            prev_val = previous_run.__project.get(*key, step=step, index=index)

            if check_val != prev_val:
                gen_reset(key)

    def check_files_changed(self, previous_run: "SchedulerNode",
                            previous_time: float, keys: Set[Tuple[str, ...]]) -> None:
        """
        Checks if any specified file-based parameters have changed.

        This check can be based on file hashes (if enabled) or timestamps.

        Args:
            previous_run (SchedulerNode): The node object from a previous run.
            previous_time (float): The timestamp of the previous run's manifest.
            keys (set of tuples): A set of file/dir keypaths to check.

        Returns:
            bool: True if any file has changed, False otherwise.
        """
        use_hash = self.__hash and previous_run.__hash

        def gen_warning(key, reason):
            raise SchedulerNodeReset(f'[{",".join(key)}] ({reason}) in {self.__step}/'
                                     f'{self.__index} has been modified from previous run')

        def get_file_time(path):
            times = [os.path.getmtime(path)]
            if os.path.isdir(path):
                for path_root, _, files in os.walk(path):
                    for path_end in files:
                        times.append(os.path.getmtime(os.path.join(path_root, path_end)))

            return max(times)

        for key in sorted(keys):
            param = self.__project.get(*key, field=None)
            step, index = self.__step, self.__index
            if param.get(field='pernode').is_never():
                step, index = None, None

            if use_hash:
                check_hash = self.__project.hash_files(*key, update=False, check=False,
                                                       verbose=False,
                                                       step=step, index=index)
                prev_hash = previous_run.__project.get(*key, field='filehash',
                                                       step=step, index=index)

                if check_hash != prev_hash:
                    gen_warning(key, "file hash")
            else:
                # check package values
                check_val = self.__project.get(*key, field='dataroot',
                                               step=step, index=index)
                prev_val = previous_run.__project.get(*key, field='dataroot',
                                                      step=step, index=index)

                if check_val != prev_val:
                    gen_warning(key, "file dataroot")

                files = self.__project.find_files(*key, step=step, index=index)
                if not isinstance(files, (list, set, tuple)):
                    files = [files]

                for check_file in files:
                    if get_file_time(check_file) > previous_time:
                        gen_warning(key, "timestamp")

    def get_check_changed_keys(self) -> Tuple[Set[Tuple[str, ...]], Set[Tuple[str, ...]]]:
        """
        Gathers all schema keys that could trigger a re-run if changed.

        This includes tool options, scripts, and required inputs specified
        in the task's schema.

        Returns:
            tuple: A tuple containing two sets: (value_keys, path_keys).
                `value_keys` are keys for simple values.
                `path_keys` are keys for file/directory paths.

        Raises:
            KeyError: If a required keypath is not found in the schema.
        """
        all_keys = set()

        all_keys.update(self.__task.get('require'))

        tool_task_prefix = ('tool', self.__task.tool(), 'task', self.__task.task())
        for key in ('option', 'threads', 'prescript', 'postscript', 'refdir', 'script',):
            all_keys.add(",".join([*tool_task_prefix, key]))

        for env_key in self.__project.getkeys(*tool_task_prefix, 'env'):
            all_keys.add(",".join([*tool_task_prefix, 'env', env_key]))

        value_keys = set()
        path_keys = set()
        for key in all_keys:
            keypath = tuple(key.split(","))
            if not self.__project.valid(*keypath, default_valid=True):
                raise KeyError(f"[{','.join(keypath)}] not found")
            keytype = self.__project.get(*keypath, field="type")
            if 'file' in keytype or 'dir' in keytype:
                path_keys.add(keypath)
            else:
                value_keys.add(keypath)

        return value_keys, path_keys

    def requires_run(self) -> None:
        """
        Determines if the node needs to be re-run.

        This method performs a series of checks against the results of a
        previous run (if one exists). It checks for changes in run status,
        configuration parameters, and input files to decide if the node's
        task can be skipped.

        Returns:
            bool: True if a re-run is required, False otherwise.
        """
        from siliconcompiler import Project

        if self.__breakpoint:
            # Breakpoint is set to must run
            raise SchedulerNodeResetSilent(f"Breakpoint is set on {self.__step}/{self.__index}")

        # Load previous manifest
        previous_node = None
        previous_node_time = time.time()
        if os.path.exists(self.__manifests["input"]):
            previous_node_time = os.path.getmtime(self.__manifests["input"])
            try:
                i_project: Project = Project.from_manifest(filepath=self.__manifests["input"])
            except:  # noqa E722
                raise SchedulerNodeResetSilent("Input manifest failed to load")
            previous_node = SchedulerNode(i_project, self.__step, self.__index)
        else:
            # No manifest found so assume rerun is needed
            raise SchedulerNodeResetSilent("Previous run did not generate input manifest")

        previous_node_end = None
        if os.path.exists(self.__manifests["output"]):
            try:
                o_project = Project.from_manifest(filepath=self.__manifests["output"])
            except:  # noqa E722
                raise SchedulerNodeResetSilent("Output manifest failed to load")
            previous_node_end = SchedulerNode(o_project, self.__step, self.__index)
        else:
            # No manifest found so assume rerun is needed
            raise SchedulerNodeResetSilent("Previous run did not generate output manifest")

        with self.runtime():
            if previous_node_end:
                with previous_node_end.runtime():
                    self.check_previous_run_status(previous_node_end)

            if previous_node:
                with previous_node.runtime():
                    # Generate key paths to check
                    try:
                        value_keys, path_keys = self.get_check_changed_keys()
                        previous_value_keys, previous_path_keys = \
                            previous_node.get_check_changed_keys()
                        value_keys.update(previous_value_keys)
                        path_keys.update(previous_path_keys)
                    except KeyError:
                        raise SchedulerNodeResetSilent("Failed to acquire keys")

                    self.check_values_changed(previous_node, value_keys.union(path_keys))
                    self.check_files_changed(previous_node, previous_node_time, path_keys)

    def setup_input_directory(self) -> None:
        """
        Prepares the 'inputs/' directory for the node's execution.

        This method gathers output files from all preceding nodes in the
        flowgraph and links or copies them into the current node's 'inputs/'
        directory. It also handles file renaming as specified by the task.
        """
        in_files = set(self.__task.get('input'))

        for in_step, in_index in self.__record.get('inputnode',
                                                   step=self.__step, index=self.__index):
            if NodeStatus.is_error(self.__record.get('status', step=in_step, index=in_index)):
                self.halt(f'Halting step due to previous error in {in_step}/{in_index}')

            output_dir = os.path.join(
                workdir(self.__project, step=in_step, index=in_index), "outputs")
            if not os.path.isdir(output_dir):
                self.halt(f'Unable to locate outputs directory for {in_step}/{in_index}: '
                          f'{output_dir}')

            for outfile in os.scandir(output_dir):
                if outfile.name == f'{self.__name}.pkg.json':
                    # Dont forward manifest
                    continue

                new_name = self.__task.compute_input_file_node_name(outfile.name, in_step, in_index)
                if self.__enforce_inputfiles:
                    if outfile.name not in in_files and new_name not in in_files:
                        continue

                if outfile.is_file() or outfile.is_symlink():
                    utils.link_symlink_copy(outfile.path,
                                            f'{self.__workdir}/inputs/{outfile.name}')
                elif outfile.is_dir():
                    shutil.copytree(outfile.path,
                                    f'{self.__workdir}/inputs/{outfile.name}',
                                    dirs_exist_ok=True,
                                    copy_function=utils.link_symlink_copy)

                if new_name in in_files:
                    # perform rename
                    os.rename(f'{self.__workdir}/inputs/{outfile.name}',
                              f'{self.__workdir}/inputs/{new_name}')

    def validate(self) -> bool:
        """
        Performs pre-run validation checks.

        This method ensures that all expected input files exist in the 'inputs/'
        directory and that all required schema parameters have been set and can
        be resolved correctly before the task is executed.

        Returns:
            bool: True if validation passes, False otherwise.
        """
        error = False

        required_inputs = self.__task.get('input')

        input_dir = os.path.join(self.__workdir, 'inputs')

        for filename in required_inputs:
            path = os.path.join(input_dir, filename)
            if not os.path.exists(path):
                self.logger.error(f'Required input {filename} not received for '
                                  f'{self.__step}/{self.__index}.')
                error = True

        all_required = self.__task.get('require')
        for item in all_required:
            keypath = item.split(',')
            if not self.__project.valid(*keypath):
                self.logger.error(f'Cannot resolve required keypath [{",".join(keypath)}].')
                error = True
                continue

            param = self.__project.get(*keypath, field=None)
            check_step, check_index = self.__step, self.__index
            if param.get(field='pernode').is_never():
                check_step, check_index = None, None

            if not param.has_value(step=check_step, index=check_index):
                self.logger.error('No value set for required keypath '
                                  f'[{",".join(keypath)}].')
                error = True
                continue

            paramtype = param.get(field='type')
            if ('file' in paramtype) or ('dir' in paramtype):
                abspath = self.__project.find_files(*keypath,
                                                    missing_ok=True,
                                                    step=check_step, index=check_index)

                unresolved_paths = param.get(step=check_step, index=check_index)
                if not isinstance(abspath, list):
                    abspath = [abspath]
                    unresolved_paths = [unresolved_paths]

                for path, setpath in zip(abspath, unresolved_paths):
                    if path is None:
                        self.logger.error(f'Cannot resolve path {setpath} in '
                                          f'required file keypath [{",".join(keypath)}].')
                        error = True

        return not error

    def summarize(self) -> None:
        """Prints a post-run summary of metrics to the logger."""
        for metric in ['errors', 'warnings']:
            val = self.__metrics.get(metric, step=self.__step, index=self.__index)
            if val is not None:
                self.logger.info(f'Number of {metric}: {val}')

        walltime = self.__metrics.get("tasktime", step=self.__step, index=self.__index)
        self.logger.info(f"Finished task in {walltime:.2f}s")

    def run(self) -> None:
        """
        Executes the full lifecycle for this node.

        This method orchestrates the entire process of running a node:
        1. Initializes logging and records metadata.
        2. Sets up the working directory.
        3. Determines and links inputs from previous nodes.
        4. Writes the pre-execution manifest.
        5. Validates that all inputs and parameters are ready.
        6. Calls `execute()` to run the tool.
        7. Stops journaling and returns to the original directory.

        Note: Since this method may run in its own process with a separate
        address space, any changes made to the schema are communicated through
        reading/writing the project manifest to the filesystem.
        """

        # Setup logger
        self._init_run_logger()

        self.__project.set('arg', 'step', self.__step)
        self.__project.set('arg', 'index', self.__index)

        # Setup journaling
        journal = Journal.access(self.__project)
        journal.start()

        # Must be after journaling to ensure journal is complete
        self.__setup_schema_access()

        # Make record of sc version and machine
        self.__record.record_version(self.__step, self.__index)

        # Record user information if enabled
        if self.__record_user_info:
            self.__record.record_userinformation(self.__step, self.__index)

        # Start wall timer
        self.__record.record_time(self.__step, self.__index, RecordTime.START)

        cwd = os.getcwd()
        with self.runtime():
            # Setup run directory
            self.__task.setup_work_directory(self.__workdir, remove_exist=not self.__replay)

            os.chdir(self.__workdir)

            # Attach siliconcompiler file log handler
            file_log = logging.FileHandler(self.__logs["sc"])
            file_log.setFormatter(
                SCInRunLoggerFormatter(self.__project, self.__job, self.__step, self.__index))
            self.logger.addHandler(file_log)

            # Select the inputs to this node
            sel_inputs = self.__task.select_input_nodes()
            if not self.__is_entry_node and not sel_inputs:
                self.halt(f'No inputs selected for {self.__step}/{self.__index}')
            self.__record.set("inputnode", sel_inputs, step=self.__step, index=self.__index)

            if self.__hash:
                self.__hash_files_pre_execute()

            # Forward data
            if not self.__replay:
                self.setup_input_directory()

            # Write manifest prior to step running into inputs
            self.__project.write_manifest(self.__manifests["input"])

            # Check manifest
            if not self.validate():
                self.halt("Failed to validate node setup. See previous errors")

            try:
                self.execute()
            except Exception as e:
                utils.print_traceback(self.logger, e)
                self.halt()

        # return to original directory
        os.chdir(cwd)

        # Stop journaling
        journal.stop()

        if self.__pipe:
            self.__pipe.send(Resolver.get_cache(self.__project))

    @contextlib.contextmanager
    def __set_env(self):
        """Temporarily sets task-specific environment variables.

        This context manager saves the current `os.environ`, updates it
        with the task's runtime variables, yields control, and then
        restores the original environment upon exiting the context.
        """
        org_env = os.environ.copy()
        try:
            os.environ.update(self.__task.get_runtime_environmental_variables())
            yield
        finally:
            os.environ.clear()
            os.environ.update(org_env)

    def get_exe_path(self) -> Optional[str]:
        """Gets the path to the requested executable for this task.

        This method retrieves the executable path from the underlying task
        object. It ensures that the task's specific runtime environment
        variables are set before making the call.

        Returns:
            Optional[str]: The file path to the executable, or None if not found.
        """
        with self.__set_env():
            return self.__task.get_exe()

    def check_version(self, version: Optional[str] = None) -> Tuple[Optional[str], bool]:
        """Checks the version of the tool for this task.

        Compares a version string against the tool's requirements. This check
        is performed within the task's specific runtime environment.

        If no `version` is provided, this method will attempt to get the
        version from the task itself. The check can be skipped if the
        project option 'novercheck' is set.

        Args:
            version: The version string to check. If None, the task's
                configured version is fetched and used.

        Returns:
            A tuple (version_str, check_passed):
                - version_str (Optional[str]): The version string that was
                  evaluated.
                - check_passed (bool): True if the version is compatible or
                  if the check was skipped, False otherwise.
        """
        if self.__project.get('option', 'novercheck', step=self.__step, index=self.__index):
            return version, True

        with self.__set_env():
            if version is None:
                version = self.__task.get_exe_version()

            check = self.__task.check_exe_version(version)

            return version, check

    def execute(self) -> None:
        """
        Handles the core tool execution logic.

        This method runs the pre-processing, execution, and post-processing
        steps for the node's task. It manages the tool's environment, checks
        for return codes, and handles log file parsing and error reporting.
        """
        from siliconcompiler import TaskSkip

        self.logger.info(f'Running in {self.__workdir}')

        try:
            self.__task.pre_process()
        except TaskSkip as skip:
            self.logger.warning(f'Removing {self.__step}/{self.__index} due to {skip.why}')
            self.__record.set('status', NodeStatus.SKIPPED, step=self.__step, index=self.__index)
        except Exception as e:
            self.logger.error(
                f"Pre-processing failed for {self.__task.tool()}/{self.__task.task()}")
            utils.print_traceback(self.logger, e)
            raise e

        if self.__record.get('status', step=self.__step, index=self.__index) == NodeStatus.SKIPPED:
            # copy inputs to outputs and skip execution
            for in_step, in_index in self.__record.get('inputnode',
                                                       step=self.__step, index=self.__index):
                required_outputs = set(self.__task.get('output'))
                in_workdir = workdir(self.__project, step=in_step, index=in_index)
                for outfile in os.scandir(f"{in_workdir}/outputs"):
                    if outfile.name == f'{self.__name}.pkg.json':
                        # Dont forward manifest
                        continue

                    if outfile.name not in required_outputs:
                        # Dont forward non-required outputs
                        continue

                    if outfile.is_file() or outfile.is_symlink():
                        utils.link_symlink_copy(outfile.path,
                                                f'outputs/{outfile.name}')
                    elif outfile.is_dir():
                        shutil.copytree(outfile.path,
                                        f'outputs/{outfile.name}',
                                        dirs_exist_ok=True,
                                        copy_function=utils.link_symlink_copy)

            send_messages.send(self.__project, "skipped", self.__step, self.__index)
        else:
            with self.__set_env():
                toolpath = self.__task.get_exe()
                version, version_pass = self.check_version()

                if not version_pass:
                    self.halt()

                if version:
                    self.__record.record_tool(self.__step, self.__index, version,
                                              RecordTool.VERSION)

                if toolpath:
                    self.__record.record_tool(self.__step, self.__index, toolpath, RecordTool.PATH)

                send_messages.send(self.__project, "begin", self.__step, self.__index)

                try:
                    if not self.__replay:
                        self.__task.generate_replay_script(self.__replay_script, self.__workdir)
                    ret_code = self.__task.run_task(
                        self.__workdir,
                        self.__project.get('option', 'quiet',
                                           step=self.__step, index=self.__index),
                        self.__breakpoint,
                        self.__project.get('option', 'nice',
                                           step=self.__step, index=self.__index),
                        self.__project.get('option', 'timeout',
                                           step=self.__step, index=self.__index))
                except Exception as e:
                    raise e

            if ret_code != 0:
                msg = f'Command failed with code {ret_code}.'
                if os.path.exists(self.__logs["exe"]):
                    if self.__project.get('option', 'quiet', step=self.__step, index=self.__index):
                        # Print last N lines of log when in quiet mode
                        with sc_open(self.__logs["exe"]) as logfd:
                            loglines = logfd.read().splitlines()
                            for logline in loglines[-self.__failed_log_lines:]:
                                self.logger.error(logline)
                    # No log file for pure-Python tools.
                    msg += f' See log file {os.path.abspath(self.__logs["exe"])}'
                self.logger.warning(msg)
                self.__error = True

            try:
                self.__task.post_process()
            except Exception as e:
                self.logger.error(
                    f"Post-processing failed for {self.__task.tool()}/{self.__task.task()}")
                utils.print_traceback(self.logger, e)
                self.__error = True

        self.check_logfile()

        if not self.__error and self.__hash:
            self.__hash_files_post_execute()

        # Capture wall runtime
        self.__record.record_time(self.__step, self.__index, RecordTime.END)
        self.__metrics.record_tasktime(self.__step, self.__index, self.__record)
        self.__metrics.record_totaltime(
            self.__step, self.__index,
            self.__flow,
            self.__record)

        # Save a successful manifest
        if self.__error:
            self.__record.set('status', NodeStatus.ERROR, step=self.__step, index=self.__index)
        elif self.__record.get('status', step=self.__step, index=self.__index) != \
                NodeStatus.SKIPPED:
            self.__record.set('status', NodeStatus.SUCCESS, step=self.__step, index=self.__index)

        self.__project.write_manifest(self.__manifests["output"])

        self.summarize()

        if self.__error and self.__generate_test_case:
            self.__generate_testcase()

        # Stop if there are errors
        errors = self.__metrics.get('errors', step=self.__step, index=self.__index)
        if errors and not self.__project.get('option', 'continue',
                                             step=self.__step, index=self.__index):
            self.halt(f'{self.__task.tool()}/{self.__task.task()} reported {errors} '
                      f'errors during {self.__step}/{self.__index}')

        if self.__error:
            self.halt()

        self.__report_output_files()

        send_messages.send(self.__project, "end", self.__step, self.__index)

    def __generate_testcase(self) -> None:
        """
        Private helper to generate a test case upon failure.

        This method packages the failing state (including manifests, inputs,
        and logs) into a compressed archive for easier debugging.
        """

        if not self.project.option.get_autoissue():
            manifest = None
            for node_manifest in self.__manifests.values():
                if os.path.exists(node_manifest):
                    manifest = node_manifest
                    break

            if manifest:
                manifest = os.path.relpath(manifest, self.__cwd)
                self.logger.error(f"To generate a testcase, run: sc-issue -cfg {manifest}")
                return

        from siliconcompiler.utils.issue import generate_testcase
        import lambdapdk

        foss_libraries = [*lambdapdk.get_pdk_names(), *lambdapdk.get_lib_names()]

        generate_testcase(
            self.__project,
            self.__step,
            self.__index,
            archive_directory=self.__jobworkdir,
            include_libraries=False,
            include_specific_libraries=foss_libraries,
            hash_files=self.__hash,
            verbose_collect=False)

    def check_logfile(self) -> None:
        """
        Parses the tool execution log file for patterns.

        This method reads the tool's log file (e.g., 'synthesis.log') and
        uses regular expressions defined in the schema to find and count
        errors, warnings, and other specified metrics. The findings are
        recorded in the schema and printed to the console.
        """
        if self.__record.get('status', step=self.__step, index=self.__index) == NodeStatus.SKIPPED:
            return

        if not os.path.exists(self.__logs["exe"]):
            return

        checks = {}
        matches = {}
        for suffix in self.__task.getkeys('regex'):
            regexes = self.__task.get('regex', suffix)
            if not regexes:
                continue

            checks[suffix] = {
                "report": open(f"{self.__step}.{suffix}", "w"),
                "args": regexes,
                "display": False
            }
            matches[suffix] = 0

        def print_error(suffix, line):
            self.logger.error(line)

        def print_warning(suffix, line):
            self.logger.warning(line)

        def print_info(suffix, line):
            self.logger.warning(f'{suffix}: {line}')

        if not self.__project.get('option', 'quiet', step=self.__step, index=self.__index):
            for suffix, info in checks.items():
                if suffix == 'errors':
                    info["display"] = print_error
                elif suffix == "warnings":
                    info["display"] = print_warning
                else:
                    info["display"] = print_info

        # Order suffixes as follows: [..., 'warnings', 'errors']
        ordered_suffixes = list(
            filter(lambda key: key not in ['warnings', 'errors'], checks.keys()))
        if 'warnings' in checks:
            ordered_suffixes.append('warnings')
        if 'errors' in checks:
            ordered_suffixes.append('errors')

        print_paths = {}
        # Looping through patterns for each line
        with sc_open(self.__logs["exe"]) as f:
            line_count = sum(1 for _ in f)
            right_align = len(str(line_count))
            for suffix in ordered_suffixes:
                print_paths[suffix] = False
                # Start at the beginning of file again
                f.seek(0)
                for num, line in enumerate(f, start=1):
                    string = line
                    for item in checks[suffix]['args']:
                        if string is None:
                            break
                        else:
                            string = utils.grep(self.__project.logger, item, string)
                    if string is not None:
                        matches[suffix] += 1
                        # always print to file
                        line_with_num = f'{num: >{right_align}}: {string.strip()}'
                        print(line_with_num, file=checks[suffix]['report'])
                        # selectively print to display
                        if checks[suffix]["display"]:
                            if matches[suffix] <= SchedulerNode.__MAX_LOG_PRINT:
                                checks[suffix]["display"](suffix, line_with_num)
                            else:
                                if not print_paths[suffix]:
                                    checks[suffix]["display"](suffix, "print limit reached")
                                print_paths[suffix] = True

        for check in checks.values():
            check['report'].close()

        for suffix in ordered_suffixes:
            if print_paths[suffix]:
                self.logger.info(f"All {suffix} can be viewed at: "
                                 f"{os.path.abspath(f'{self.__step}.{suffix}')}")

        for metric in ("errors", "warnings"):
            if metric in matches:
                value = self.__metrics.get(metric, step=self.__step, index=self.__index)
                if value is None:
                    value = 0
                value += matches[metric]

                sources = [os.path.basename(self.__logs["exe"])]
                if self.__task.get('regex', metric):
                    sources.append(f'{self.__step}.{metric}')

                self.__task.record_metric(metric, value, source_file=sources)

    def __hash_files_pre_execute(self) -> None:
        """Private helper to hash all relevant input files before execution."""
        for task_key in ('refdir', 'prescript', 'postscript', 'script'):
            self.__project.hash_files('tool', self.__task.tool(),
                                      'task', self.__task.task(), task_key,
                                      step=self.__step, index=self.__index, check=False,
                                      verbose=False)

        # hash all requirements
        for item in set(self.__task.get('require')):
            args = item.split(',')
            sc_type = self.__project.get(*args, field='type')
            if 'file' in sc_type or 'dir' in sc_type:
                access_step, access_index = self.__step, self.__index
                if self.__project.get(*args, field='pernode').is_never():
                    access_step, access_index = None, None
                self.__project.hash_files(*args, step=access_step, index=access_index,
                                          check=False, verbose=False)

    def __hash_files_post_execute(self) -> None:
        """Private helper to hash all output files after execution."""
        # hash all outputs
        self.__project.hash_files('tool', self.__task.tool(), 'task', self.__task.task(), 'output',
                                  step=self.__step, index=self.__index, check=False, verbose=False)

        # hash all requirements
        for item in set(self.__task.get('require')):
            args = item.split(',')
            sc_type = self.__project.get(*args, field='type')
            if 'file' in sc_type or 'dir' in sc_type:
                access_step, access_index = self.__step, self.__index
                if self.__project.get(*args, field='pernode').is_never():
                    access_step, access_index = None, None
                if self.__project.get(*args, field='filehash'):
                    continue
                self.__project.hash_files(*args, step=access_step, index=access_index,
                                          check=False, verbose=False)

    def __report_output_files(self) -> None:
        """
        Private helper to check for missing or unexpected output files.

        Compares the files found in the 'outputs/' directory against the
        files expected by the task's schema. Reports errors if they don't match.
        """
        if self.is_builtin:
            return

        error = False

        try:
            outputs = os.listdir(os.path.join(self.__workdir, "outputs"))
        except FileNotFoundError:
            self.halt("Output directory is missing")

        try:
            outputs.remove(os.path.basename(self.__manifests["output"]))
        except ValueError:
            self.logger.error(f"Output manifest ({os.path.basename(self.__manifests['output'])}) "
                              "is missing.")
            error = True

        outputs = set(outputs)

        output_files = set(self.__task.get('output'))

        missing = output_files.difference(outputs)
        excess = outputs.difference(output_files)

        if missing:
            error = True
            self.logger.error(f"Expected output files are missing: {', '.join(missing)}")

        if excess:
            error = True
            self.logger.error(f"Unexpected output files found: {', '.join(excess)}")

        if error and self.__enforce_outputfiles:
            self.halt()

    def copy_from(self, source: str) -> None:
        """
        Imports the results of this node from a different job run.

        This method copies the entire working directory of a node from a
        specified source job into the current job's working directory. It is
        used for resuming or branching from a previous run.

        Args:
            source (str): The jobname of the source run to copy from.
        """
        from siliconcompiler import Project

        org_name = self.__project.get("option", "jobname")
        self.__project.set("option", "jobname", source)
        copy_from = workdir(self.__project, step=self.__step, index=self.__index)
        self.__project.set("option", "jobname", org_name)

        if not os.path.exists(copy_from):
            return

        self.logger.info(f'Importing {self.__step}/{self.__index} from {source}')
        shutil.copytree(
            copy_from, self.__workdir,
            dirs_exist_ok=True,
            copy_function=utils.link_copy)

        # rewrite replay files
        if os.path.exists(self.__replay_script):
            # delete file as it might be a hard link
            os.remove(self.__replay_script)

            with self.runtime():
                self.__task.generate_replay_script(self.__replay_script, self.__workdir)

        for manifest in self.__manifests.values():
            if os.path.exists(manifest):
                schema = Project.from_manifest(filepath=manifest)
                # delete file as it might be a hard link
                os.remove(manifest)
                schema.set('option', 'jobname', self.__job)
                schema.write_manifest(manifest)

    def clean_directory(self) -> None:
        """Removes the working directory for this node."""
        if os.path.exists(self.__workdir):
            shutil.rmtree(self.__workdir)

    def archive(self, tar: tarfile.TarFile,
                include: Optional[List[str]] = None,
                verbose: bool = False) -> None:
        """
        Archives the node's results into a tar file.

        By default, it archives the 'reports' and 'outputs' directories and all
        log files. The `include` argument allows for custom file selection using
        glob patterns.

        Args:
            tar (tarfile.TarFile): The tarfile object to add files to.
            include (List[str], optional): A list of glob patterns to specify
                which files to include in the archive. Defaults to None.
            verbose (bool, optional): If True, prints archiving status messages.
                Defaults to None.
        """
        if not tar:
            return

        if verbose:
            self.logger.info(f'Archiving {self.step}/{self.index}...')

        def arcname(path):
            return os.path.relpath(path, self.__cwd)

        if not os.path.isdir(self.__workdir):
            if self.project.get('record', 'status', step=self.step, index=self.index) != \
                    NodeStatus.SKIPPED:
                self.logger.error(f'Unable to archive {self.step}/{self.index} '
                                  'due to missing node directory')
            return

        if include:
            if isinstance(include, str):
                include = [include]
            for pattern in include:
                for path in glob.iglob(os.path.join(self.__workdir, pattern)):
                    tar.add(path, arcname=arcname(path))
        else:
            for folder in ('reports', 'outputs'):
                path = os.path.join(self.__workdir, folder)
                tar.add(path, arcname=arcname(path))

            for logfile in self.__logs.values():
                if os.path.isfile(logfile):
                    tar.add(logfile, arcname=arcname(logfile))

    def get_required_keys(self) -> Set[Tuple[str, ...]]:
        """
        This function walks through the 'require' keys and returns the
        keys.
        """
        path_keys = set()
        with self.runtime():
            task = self.task
            for key in task.get('require'):
                path_keys.add(tuple(key.split(",")))
            if task.has_prescript():
                path_keys.add((*task._keypath, "prescript"))
            if task.has_postscript():
                path_keys.add((*task._keypath, "postscript"))
            if task.get("refdir"):
                path_keys.add((*task._keypath, "refdir"))
            if task.get("script"):
                path_keys.add((*task._keypath, "script"))
            if task.get("exe"):
                path_keys.add((*task._keypath, "exe"))

        return path_keys

    def get_required_path_keys(self) -> Set[Tuple[str, ...]]:
        """
        This function walks through the 'require' keys and returns the
        keys that are of type path (file/dir).
        """
        path_keys = set()
        for key in self.get_required_keys():
            try:
                param_type: str = self.__project.get(*key, field="type")
                if "file" in param_type or "dir" in param_type:
                    path_keys.add(key)
            except KeyError:
                # Key does not exist
                pass

        return path_keys

    def mark_copy(self) -> bool:
        """Marks files from the 'require' path keys for copying."""
        return False

    def check_required_values(self) -> bool:
        requires = self.get_required_keys()

        error = False
        for key in sorted(requires):
            if not self.__project.valid(*key):
                self.logger.error(f'Cannot resolve required keypath [{",".join(key)}] '
                                  f'for {self.step}/{self.index}.')
                error = True
                continue

            param: Parameter = self.__project.get(*key, field=None)
            check_step, check_index = self.step, self.index
            if param.get(field='pernode').is_never():
                check_step, check_index = None, None

            if not param.has_value(step=check_step, index=check_index):
                self.logger.error('No value set for required keypath '
                                  f'[{",".join(key)}] for {self.step}/{self.index}.')
                error = True
                continue
        return not error

    def check_required_paths(self) -> bool:
        if self.__project.option.get_remote():
            return True

        requires = self.get_required_path_keys()

        error = False
        for key in sorted(requires):
            param: Parameter = self.__project.get(*key, field=None)
            check_step, check_index = self.step, self.index
            if param.get(field='pernode').is_never():
                check_step, check_index = None, None

            abspath = self.__project.find_files(*key,
                                                missing_ok=True,
                                                step=check_step, index=check_index)

            unresolved_paths = param.get(step=check_step, index=check_index)
            if not isinstance(abspath, list):
                abspath = [abspath]
                unresolved_paths = [unresolved_paths]

            for path, setpath in zip(abspath, unresolved_paths):
                if path is None:
                    self.logger.error(f'Cannot resolve path {setpath} in '
                                      f'required file keypath [{",".join(key)}] '
                                      f'for {self.step}/{self.index}.')
                    error = True
        return not error
