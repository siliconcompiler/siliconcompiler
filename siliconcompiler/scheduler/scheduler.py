import io
import logging
import os
import re
import shutil
import sys
import traceback

import os.path

from siliconcompiler import NodeStatus
from siliconcompiler.schema import Journal
from siliconcompiler.flowgraph import RuntimeFlowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.scheduler import SlurmSchedulerNode
from siliconcompiler.scheduler import DockerSchedulerNode
from siliconcompiler.scheduler import TaskScheduler
from siliconcompiler.scheduler.schedulernode import SchedulerFlowReset

from siliconcompiler import utils
from siliconcompiler.utils.logging import SCLoggerFormatter
from siliconcompiler.utils.multiprocessing import MPManager
from siliconcompiler.scheduler import send_messages, SCRuntimeError
from siliconcompiler.utils.paths import collectiondir, jobdir, workdir


class Scheduler:
    """
    A class for orchestrating and executing a compilation flowgraph.

    The Scheduler is responsible for managing the entire lifecycle of a compilation
    run. It interprets the flowgraph defined in the Project object, determines which
    nodes (steps) need to be run based on user settings (like 'from', 'to') and
    the state of previous runs, and then executes the tasks in the correct order.

    It handles setting up individual task nodes, managing dependencies, logging,
    and reporting results.
    """

    def __init__(self, project):
        """
        Initializes the Scheduler.

        Args:
            project (Project): The Project object containing the configuration and flowgraph.

        Raises:
            SCRuntimeError: If the specified flow is not defined or fails validation.
        """
        self.__project = project
        self.__logger: logging.Logger = project.logger
        self.__name = project.name

        flow = self.__project.get("option", "flow")
        if not flow:
            raise SCRuntimeError("flow must be specified")

        if flow not in self.__project.getkeys("flowgraph"):
            raise SCRuntimeError("flow is not defined")

        self.__flow = self.__project.get("flowgraph", flow, field="schema")
        from_steps = self.__project.get('option', 'from')
        to_steps = self.__project.get('option', 'to')
        prune_nodes = self.__project.get('option', 'prune')

        if not self.__flow.validate(logger=self.__logger):
            raise SCRuntimeError(f"{self.__flow.name} flowgraph contains errors and cannot be run.")
        if not RuntimeFlowgraph.validate(
                self.__flow,
                from_steps=from_steps,
                to_steps=to_steps,
                prune_nodes=prune_nodes,
                logger=self.__logger):
            raise SCRuntimeError(f"{self.__flow.name} flowgraph contains errors and cannot be run.")

        self.__flow_runtime = RuntimeFlowgraph(
            self.__flow,
            from_steps=from_steps,
            to_steps=to_steps,
            prune_nodes=self.__project.get('option', 'prune'))

        self.__flow_load_runtime = RuntimeFlowgraph(
            self.__flow,
            to_steps=from_steps,
            prune_nodes=prune_nodes)

        self.__record = self.__project.get("record", field="schema")
        self.__metrics = self.__project.get("metric", field="schema")

        self.__tasks = {}

        # Create dummy handler
        self.__joblog_handler = logging.NullHandler()
        self.__org_job_name = self.__project.get("option", "jobname")
        self.__logfile = None

    @property
    def log(self) -> str:
        """
        Returns path to the running job log
        """
        return self.__logfile

    @property
    def project(self):
        """
        Returns the Project object associated with this scheduler.

        This property provides access to the central Project object, which holds
        the entire design configuration, flowgraph, and results.

        Returns:
            Project: The Project object for the current project.
        """
        return self.__project

    def __print_status(self, header):
        """
        Private helper to print the current status of all nodes for debugging.

        Args:
            header (str): A header message to print before the status list.
        """
        self.__logger.debug(f"#### {header}")
        for step, index in self.__flow.get_nodes():
            self.__logger.debug(f"({step}, {index}) -> "
                                f"{self.__record.get('status', step=step, index=index)}")
        self.__logger.debug("####")

    def check_manifest(self):
        """
        Checks the validity of the Project's manifest before a run.

        Returns:
            bool: True if the manifest is valid, False otherwise.
        """
        self.__logger.info("Checking manifest before running.")
        return self.__project.check_manifest()

    def run_core(self):
        """
        Executes the core task scheduling loop.

        This method initializes and runs the TaskScheduler, which manages the
        execution of individual nodes based on their dependencies and status.
        """
        self.__record.record_python_packages()

        task_scheduler = TaskScheduler(self.__project, self.__tasks)
        task_scheduler.run(self.__joblog_handler)
        task_scheduler.check()

    def __excepthook(self, exc_type, exc_value, exc_traceback):
        """
        Handle uncaught exceptions by recording them to the job log, emitting a full traceback,
        stopping any running dashboard, and notifying the multiprocessing manager.

        Logs a concise exception summary and the full traceback to the scheduler's job logger,
        forwards KeyboardInterrupt to the default system excepthook, invokes the
        project's dashboard stop method when present, and signals an uncaught exception
        to the multiprocessing manager.

        Parameters:
            exc_type (Type[BaseException]): Exception class of the uncaught exception.
            exc_value (BaseException): Exception instance (may contain the message).
            exc_traceback (types.TracebackType): Traceback object for the exception.
        """
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # Print a summary of the exception
        except_msg = f"Exception raised: {exc_type.__name__}"
        exc_value = str(exc_value).strip()
        if exc_value:
            except_msg += f" / {exc_value}"
        self.__logger.error(except_msg)

        trace = io.StringIO()

        # Print the full traceback for debugging
        self.__logger.error("Traceback (most recent call last):")
        traceback.print_tb(exc_traceback, file=trace)
        for line in trace.getvalue().splitlines():
            self.__logger.error(line)

        # Ensure dashboard receives a stop if running
        if self.__project._Project__dashboard:
            self.__project._Project__dashboard.stop()

        # Mark error to keep logfile
        MPManager.error("uncaught exception")

    def __install_file_logger(self):
        """
        Set up a per-job file logger for the current project and attach it to the
        scheduler's logger.

        Creates the job directory if needed, rotates an existing job.log to a .bak
        (using incrementing numeric suffixes if necessary), installs a FileHandler
        writing to job.log with the SCLoggerFormatter, and stores the handler on
        self.__joblog_handler.
        """
        os.makedirs(jobdir(self.__project), exist_ok=True)
        file_log = os.path.join(jobdir(self.__project), "job.log")
        bak_count = 0
        bak_file_log = f"{file_log}.bak"
        while os.path.exists(bak_file_log):
            bak_count += 1
            bak_file_log = f"{file_log}.bak.{bak_count}"
        if os.path.exists(file_log):
            os.rename(file_log, bak_file_log)
        self.__logfile = file_log
        self.__joblog_handler = logging.FileHandler(file_log)
        self.__joblog_handler.setFormatter(SCLoggerFormatter())
        self.__logger.addHandler(self.__joblog_handler)

    def run(self):
        """
        The main entry point to start the compilation flow.

        This method orchestrates the entire run, including:
        - Setting up a custom exception hook for logging.
        - Initializing the job directory and log files.
        - Configuring and setting up all nodes in the flow.
        - Validating the manifest.
        - Executing the core run loop.
        - Recording the final results and history.
        """
        # Install hook to ensure exception is logged
        org_excepthook = sys.excepthook
        sys.excepthook = self.__excepthook

        try:
            # Determine job name first so we can create a log
            if not self.__increment_job_name():
                # No need to copy, no remove org job name
                self.__org_job_name = None

            # Clean the directory early if needed
            self.__clean_build_dir_full()

            # Install job file logger
            self.__install_file_logger()

            # Configure run
            self.__project._init_run()

            # Check validity of setup
            if not self.check_manifest():
                raise SCRuntimeError("check_manifest() failed")

            self.__run_setup()
            self.configure_nodes()

            # Verify tool setups
            if not self.__check_tool_requirements():
                raise SCRuntimeError("Tools requirements not met")

            # Cleanup build directory
            self.__clean_build_dir_incr()

            # Check validity of flowgraphs IO
            if not self.__check_flowgraph_io():
                raise SCRuntimeError("Flowgraph file IO constrains errors")

            self.run_core()

            # Store run in history
            self.__project._record_history()

            # Record final manifest
            filepath = os.path.join(jobdir(self.__project), f"{self.__name}.pkg.json")
            self.__project.write_manifest(filepath)

            send_messages.send(self.__project, 'summary', None, None)
        finally:
            if self.__joblog_handler is not None:
                self.__logger.removeHandler(self.__joblog_handler)
                self.__joblog_handler.close()
                self.__joblog_handler = logging.NullHandler()
            # Restore hook
            sys.excepthook = org_excepthook

    def __check_tool_requirements(self):
        """
        Performs pre-run validation checks.

        This method ensures that all expected input files exist in the 'inputs/'
        directory and that all required schema parameters have been set and can
        be resolved correctly before the task is executed.

        Returns:
            bool: True if validation passes, False otherwise.
        """
        error = False

        for (step, index) in self.__flow_runtime.get_nodes():
            scheduler = self.__project.option.scheduler.get_name(step=step, index=index)
            check_file_access = not self.__project.option.get_remote() and scheduler is None

            node = SchedulerNode(self.__project, step, index)
            requires = []
            with node.runtime():
                requires = node.task.get('require')

            for item in sorted(set(requires)):
                keypath = item.split(',')
                if not self.__project.valid(*keypath):
                    self.__logger.error(f'Cannot resolve required keypath [{",".join(keypath)}] '
                                        f'for {step}/{index}.')
                    error = True
                    continue

                param = self.__project.get(*keypath, field=None)
                check_step, check_index = step, index
                if param.get(field='pernode').is_never():
                    check_step, check_index = None, None

                if not param.has_value(step=check_step, index=check_index):
                    self.__logger.error('No value set for required keypath '
                                        f'[{",".join(keypath)}] for {step}/{index}.')
                    error = True
                    continue

                paramtype = param.get(field='type')
                if check_file_access and (('file' in paramtype) or ('dir' in paramtype)):
                    abspath = self.__project.find_files(*keypath,
                                                        missing_ok=True,
                                                        step=check_step, index=check_index)

                    unresolved_paths = param.get(step=check_step, index=check_index)
                    if not isinstance(abspath, list):
                        abspath = [abspath]
                        unresolved_paths = [unresolved_paths]

                    for path, setpath in zip(abspath, unresolved_paths):
                        if path is None:
                            self.__logger.error(f'Cannot resolve path {setpath} in '
                                                f'required file keypath [{",".join(keypath)}] '
                                                f'for {step}/{index}.')
                            error = True

        return not error

    def __check_flowgraph_io(self):
        """
        Validate that every runtime node will receive its required input files and that no
        input file is provided by more than one source.

        Checks whether each node's required inputs are available either from upstream
        tasks' declared outputs or from existing output directories, and logs errors
        for missing or duplicated input sources.

        Returns:
            bool: `True` if the flowgraph satisfies input/output requirements, `False` otherwise.
        """
        nodes = self.__flow_runtime.get_nodes()
        error = False

        for (step, index) in nodes:
            # Get files we receive from input nodes.
            in_nodes = self.__flow_runtime.get_node_inputs(step, index, record=self.__record)
            all_inputs = set()
            tool = self.__flow.get(step, index, "tool")
            task = self.__flow.get(step, index, "task")
            task_class = self.__project.get("tool", tool, "task", task, field="schema")
            requirements = task_class.get('input', step=step, index=index)

            for in_step, in_index in in_nodes:
                if (in_step, in_index) not in nodes:
                    # If we're not running the input step, the required
                    # inputs need to already be copied into the build
                    # directory.
                    in_step_out_dir = os.path.join(
                        workdir(self.__project, step=in_step, index=in_index), 'outputs')

                    if not os.path.isdir(in_step_out_dir):
                        # This means this step hasn't been run, but that
                        # will be flagged by a different check. No error
                        # message here since it would be redundant.
                        inputs = []
                        continue

                    design = self.__project.get("option", 'design')
                    manifest = f'{design}.pkg.json'
                    inputs = [inp for inp in os.listdir(in_step_out_dir) if inp != manifest]
                else:
                    in_tool = self.__flow.get(in_step, in_index, "tool")
                    in_task = self.__flow.get(in_step, in_index, "task")
                    in_task_class = self.__project.get("tool", in_tool, "task", in_task,
                                                       field="schema")

                    with in_task_class.runtime(SchedulerNode(self.__project,
                                                             in_step, in_index)) as task:
                        inputs = task.get_output_files()

                with task_class.runtime(SchedulerNode(self.__project,
                                                      step, index)) as task:
                    for inp in inputs:
                        node_inp = task.compute_input_file_node_name(inp, in_step, in_index)
                        if node_inp in requirements:
                            inp = node_inp
                        if inp in all_inputs:
                            self.__logger.error(f'Invalid flow: {step}/{index} '
                                                f'receives {inp} from multiple input tasks')
                            error = True
                        all_inputs.add(inp)

            for requirement in requirements:
                if requirement not in all_inputs:
                    self.__logger.error(f'Invalid flow: {step}/{index} will '
                                        f'not receive required input {requirement}.')
                    error = True

        return not error

    def __mark_pending(self, step, index):
        """
        Private helper to recursively mark a node and its dependents as PENDING.

        When a node is determined to need a re-run, this function ensures that
        it and all subsequent nodes in the flowgraph are marked as PENDING,
        effectively queueing them for execution.

        Args:
            step (str): The step of the node to mark.
            index (str): The index of the node to mark.
        """
        if (step, index) not in self.__flow_runtime.get_nodes():
            return

        self.__record.set('status', NodeStatus.PENDING, step=step, index=index)
        for next_step, next_index in self.__flow_runtime.get_nodes_starting_at(step, index):
            if self.__record.get('status', step=next_step, index=next_index) == NodeStatus.SKIPPED:
                continue

            # Mark following steps as pending
            self.__record.set('status', NodeStatus.PENDING, step=next_step, index=next_index)

    def __run_setup(self):
        """
        Private helper to perform initial setup for the entire run.

        This includes checking for a display environment, creating SchedulerNode
        objects for each task, and copying results from a previous job if one
        is specified.
        """
        self.__check_display()

        # Create tasks
        copy_from_nodes = set(self.__flow_load_runtime.get_nodes()).difference(
            self.__flow_runtime.get_entry_nodes())
        for step, index in self.__flow.get_nodes():
            node_cls = SchedulerNode

            node_scheduler = self.__project.get('option', 'scheduler', 'name',
                                                step=step, index=index)
            if node_scheduler == 'slurm':
                node_cls = SlurmSchedulerNode
            elif node_scheduler == 'docker':
                node_cls = DockerSchedulerNode
            self.__tasks[(step, index)] = node_cls(self.__project, step, index)
            if self.__flow.get(step, index, "tool") == "builtin":
                self.__tasks[(step, index)].set_builtin()

            if self.__org_job_name and (step, index) in copy_from_nodes:
                self.__tasks[(step, index)].copy_from(self.__org_job_name)

        if self.__org_job_name:
            # Copy collection directory
            curret_job = self.__project.get("option", "jobname")
            self.__project.set("option", "jobname", self.__org_job_name)
            copy_from = collectiondir(self.__project)
            self.__project.set("option", "jobname", curret_job)
            copy_to = collectiondir(self.__project)
            if os.path.exists(copy_from):
                shutil.copytree(copy_from, copy_to,
                                dirs_exist_ok=True,
                                copy_function=utils.link_copy)

        self.__reset_flow_nodes()

    def __reset_flow_nodes(self):
        """
        Private helper to reset the status and metrics for all nodes in the flow.

        This prepares the schema for a new run by clearing out results from any
        previous executions.
        """
        # Reset record
        for step, index in self.__flow.get_nodes():
            self.__record.clear(step, index, keep=['remoteid', 'status', 'pythonpackage'])
            self.__record.set('status', NodeStatus.PENDING, step=step, index=index)

        # Reset metrics
        for step, index in self.__flow.get_nodes():
            self.__metrics.clear(step, index)

    def __clean_build_dir_full(self, recheck: bool = False):
        """
        Remove stale build outputs from the current job directory to prepare for a fresh run.

        When executed, deletes all files and subdirectories under the job directory for the current
        project. If recheck is True, the method preserves an existing job.log file and leaves it
        untouched. The method is a no-op if the run is associated with a remote job
        (record.remoteid). When recheck is False, the cleanup only proceeds if the
        project's 'option.clean' is true and 'option.from' is not set; when recheck is
        True those option checks are bypassed.

        Parameters:
            recheck (bool): If True, perform a recheck cleanup that preserves job.log;
                            also bypasses the usual option checks. Defaults to False.
        """
        if self.__record.get('remoteid'):
            return

        if not recheck:
            if not self.__project.get('option', 'clean') or self.__project.get('option', 'from'):
                return

        # If no step or nodes to start from were specified, the whole flow is being run
        # start-to-finish. Delete the build dir to clear stale results.
        cur_job_dir = jobdir(self.__project)
        if os.path.isdir(cur_job_dir):
            for delfile in os.listdir(cur_job_dir):
                if delfile == "job.log" and recheck:
                    continue
                if os.path.isfile(os.path.join(cur_job_dir, delfile)):
                    os.remove(os.path.join(cur_job_dir, delfile))
                else:
                    shutil.rmtree(os.path.join(cur_job_dir, delfile))

    def __clean_build_dir_incr(self):
        """
        Prune the job build directory to match the current flow and clean pending node directories.

        Removes step directories and index subdirectories that are not present in the current
        flow/runtime. For nodes whose recorded status indicates they are waiting, enters the
        node's runtime context and invokes its clean_directory method to perform
        node-specific cleanup.
        """
        protected_dirs = {os.path.basename(collectiondir(self.__project))}

        keep_steps = set([step for step, _ in self.__flow.get_nodes()])
        cur_job_dir = jobdir(self.__project)
        for step in os.listdir(cur_job_dir):
            if step in protected_dirs:
                continue
            if not os.path.isdir(os.path.join(cur_job_dir, step)):
                continue
            if step not in keep_steps:
                shutil.rmtree(os.path.join(cur_job_dir, step))
        for step in os.listdir(cur_job_dir):
            if step in protected_dirs:
                continue
            if not os.path.isdir(os.path.join(cur_job_dir, step)):
                continue
            for index in os.listdir(os.path.join(cur_job_dir, step)):
                if not os.path.isdir(os.path.join(cur_job_dir, step, index)):
                    continue
                if (step, index) not in self.__flow.get_nodes():
                    shutil.rmtree(os.path.join(cur_job_dir, step, index))

        # Clean nodes marked pending
        for step, index in self.__flow_runtime.get_nodes():
            if NodeStatus.is_waiting(self.__record.get('status', step=step, index=index)):
                with self.__tasks[(step, index)].runtime():
                    self.__tasks[(step, index)].clean_directory()

    def configure_nodes(self):
        """
        Prepare and configure all flow nodes before execution, including loading prior run state,
        running per-node setup, and marking nodes that require rerun.

        This method:
        - Loads available node manifests from previous jobs and uses them to populate setup data
          where appropriate.
        - Runs each node's setup routine to initialize tools and runtime state.
        - For nodes whose parameters or inputs have changed, marks them and all downstream nodes
          as pending so they will be re-executed.
        - Replays preserved journaled results for nodes that remain valid to reuse previous outputs.
        - On a SchedulerFlowReset, forces a full build-directory recheck and marks every node
          as pending.
        - Persists the resulting manifest for the current job before returning.
        """
        from siliconcompiler import Project

        from_nodes = []
        extra_setup_nodes = {}

        journal = Journal.access(self.__project)
        journal.start()

        self.__print_status("Start")

        if self.__project.get('option', 'clean'):
            if self.__project.get("option", "from"):
                from_nodes = self.__flow_runtime.get_entry_nodes()
            load_nodes = self.__flow.get_nodes()
        else:
            if self.__project.get("option", "from"):
                from_nodes = self.__flow_runtime.get_entry_nodes()
            load_nodes = self.__flow_load_runtime.get_nodes()

        # Collect previous run information
        for step, index in self.__flow.get_nodes():
            if (step, index) not in load_nodes:
                # Node not marked for loading
                continue
            if (step, index) in from_nodes:
                # Node will be run so no need to load
                continue

            manifest = os.path.join(workdir(self.__project, step=step, index=index),
                                    'outputs',
                                    f'{self.__name}.pkg.json')
            if os.path.exists(manifest):
                # ensure we setup these nodes again
                try:
                    extra_setup_nodes[(step, index)] = Project.from_manifest(filepath=manifest)
                except Exception:
                    pass

        # Setup tools for all nodes to run
        for layer_nodes in self.__flow.get_execution_order():
            for step, index in layer_nodes:
                with self.__tasks[(step, index)].runtime():
                    node_kept = self.__tasks[(step, index)].setup()
                if not node_kept and (step, index) in extra_setup_nodes:
                    # remove from previous node data
                    del extra_setup_nodes[(step, index)]

                if (step, index) in extra_setup_nodes:
                    schema = extra_setup_nodes[(step, index)]
                    node_status = None
                    try:
                        node_status = schema.get('record', 'status', step=step, index=index)
                    except:  # noqa E722
                        pass
                    if node_status:
                        # Forward old status
                        self.__record.set('status', node_status, step=step, index=index)

        self.__print_status("After setup")

        # Check for modified information
        try:
            replay = []
            for layer_nodes in self.__flow.get_execution_order():
                for step, index in layer_nodes:
                    # Only look at successful nodes
                    if self.__record.get("status", step=step, index=index) != NodeStatus.SUCCESS:
                        continue

                    with self.__tasks[(step, index)].runtime():
                        if self.__tasks[(step, index)].requires_run():
                            # This node must be run
                            self.__mark_pending(step, index)
                        elif (step, index) in extra_setup_nodes:
                            # import old information
                            replay.append((step, index))
            # Replay previous information
            for step, index in replay:
                Journal.access(extra_setup_nodes[(step, index)]).replay(self.__project)
        except SchedulerFlowReset:
            # Mark all nodes as pending
            self.__clean_build_dir_full(recheck=True)

            for step, index in self.__flow.get_nodes():
                self.__mark_pending(step, index)

        self.__print_status("After requires run")

        # Ensure all nodes are marked as pending if needed
        for layer_nodes in self.__flow_runtime.get_execution_order():
            for step, index in layer_nodes:
                status = self.__record.get("status", step=step, index=index)
                if NodeStatus.is_waiting(status) or NodeStatus.is_error(status):
                    self.__mark_pending(step, index)

        self.__print_status("After ensure")

        os.makedirs(jobdir(self.__project), exist_ok=True)
        self.__project.write_manifest(os.path.join(jobdir(self.__project),
                                                   f"{self.__name}.pkg.json"))
        journal.stop()

    def __check_display(self):
        """
        Private helper to automatically disable GUI display on headless systems.

        If running on Linux without a DISPLAY or WAYLAND_DISPLAY environment
        variable, this sets ['option', 'nodisplay'] to True to prevent tools
        from attempting to open a GUI.
        """

        if not self.__project.get('option', 'nodisplay') and sys.platform == 'linux' \
                and 'DISPLAY' not in os.environ and 'WAYLAND_DISPLAY' not in os.environ:
            self.__logger.warning('Environment variable $DISPLAY or $WAYLAND_DISPLAY not set')
            self.__logger.warning("Setting [option,nodisplay] to True")
            self.__project.set('option', 'nodisplay', True)

    def __increment_job_name(self):
        """
        Private helper to auto-increment the jobname if ['option', 'jobincr'] is True.

        This prevents overwriting previous job results by finding the highest
        numbered existing job directory and creating a new one with an
        incremented number.

        Returns:
            bool: True if the job name was incremented, False otherwise.
        """
        if not self.__project.get('option', 'clean'):
            return False
        if not self.__project.get('option', 'jobincr'):
            return False

        workdir = jobdir(self.__project)
        if os.path.isdir(workdir):
            # Strip off digits following jobname, if any
            stem = self.__project.get('option', 'jobname').rstrip('0123456789')

            dir_check = re.compile(fr'{stem}(\d+)')

            jobid = 0
            for job in os.listdir(os.path.dirname(workdir)):
                m = dir_check.match(job)
                if m:
                    jobid = max(jobid, int(m.group(1)))
            self.__project.set('option', 'jobname', f'{stem}{jobid + 1}')
            return True
        return False
