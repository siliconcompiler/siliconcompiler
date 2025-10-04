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
from siliconcompiler.scheduler import send_messages
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
            ValueError: If the specified flow is not defined or fails validation.
        """
        self.__project = project
        self.__logger: logging.Logger = project.logger
        self.__name = project.name

        flow = self.__project.get("option", "flow")
        if not flow:
            raise ValueError("flow must be specified")

        if flow not in self.__project.getkeys("flowgraph"):
            raise ValueError("flow is not defined")

        self.__flow = self.__project.get("flowgraph", flow, field="schema")
        from_steps = self.__project.get('option', 'from')
        to_steps = self.__project.get('option', 'to')
        prune_nodes = self.__project.get('option', 'prune')

        if not self.__flow.validate(logger=self.__logger):
            raise ValueError(f"{self.__flow.name} flowgraph contains errors and cannot be run.")
        if not RuntimeFlowgraph.validate(
                self.__flow,
                from_steps=from_steps,
                to_steps=to_steps,
                prune_nodes=prune_nodes,
                logger=self.__logger):
            raise ValueError(f"{self.__flow.name} flowgraph contains errors and cannot be run.")

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
        Handle uncaught exceptions by logging a concise summary and the full traceback, stopping any active dashboard, and signaling the error to MPManager.
        
        KeyboardInterrupt is delegated to Python's default excepthook.
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
        Ensure the project's job directory exists, rotate any existing job.log to a numbered .bak, and attach a new file log handler to the scheduler's logger.
        
        Creates the job directory if missing, moves an existing job.log to job.log.bak, job.log.bak.1, job.log.bak.2, ... as needed to avoid overwriting, then installs a new FileHandler for job.log, sets its formatter, and stores the handler on self.__joblog_handler while adding it to self.__logger.
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
        self.__joblog_handler = logging.FileHandler(file_log)
        self.__joblog_handler.setFormatter(SCLoggerFormatter())
        self.__logger.addHandler(self.__joblog_handler)

    def run(self):
        """
        Orchestrates and executes a complete compilation flow for the associated project.
        
        Performs run initialization, prepares job logging and directories, validates the manifest, configures and executes flow nodes, performs runtime IO checks, records run history and the final manifest into the job directory, and emits a final summary message. Temporarily replaces the global exception hook to ensure uncaught exceptions are logged and restores the original hook on completion.
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
                raise RuntimeError("check_manifest() failed")

            self.__run_setup()
            self.configure_nodes()

            # Cleanup build directory
            self.__clean_build_dir_incr()

            # Check validity of flowgraphs IO
            if not self.__check_flowgraph_io():
                raise RuntimeError("Flowgraph file IO constrains errors")

            self.run_core()

            # Store run in history
            self.__project._record_history()

            # Record final manifest
            filepath = os.path.join(jobdir(self.__project), f"{self.__name}.pkg.json")
            self.__project.write_manifest(filepath)

            send_messages.send(self.__project, 'summary', None, None)

            self.__logger.removeHandler(self.__joblog_handler)
            self.__joblog_handler = logging.NullHandler()
        finally:
            # Restore hook
            sys.excepthook = org_excepthook

    def __check_flowgraph_io(self):
        """
        Validate that every node in the flowgraph will receive its required input files exactly once.
        
        Checks each node's declared input requirements against files produced by upstream nodes or present
        in upstream output directories. For inputs produced by steps not included in the current run, the
        function verifies the existence of the upstream step's outputs directory. For inputs produced by
        steps in the current run, the function queries the producing task's runtime to obtain its output
        file names and maps them to the consuming node's expected input names. The function logs errors
        for any required input that is missing or for any input provided by multiple upstream sources.
        
        Returns:
            bool: `True` if all nodes have every required input supplied exactly once, `False` otherwise.
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
        Remove the current job's build directory contents when a full clean is required.
        
        Performs a full cleanup of the job directory unless a remote build is active or
        cleaning is not requested or a `from` option is set. When `recheck` is True,
        preserves an existing `job.log` file; otherwise all files and subdirectories
        under the job directory are deleted.
        
        Parameters:
            recheck (bool): If True, preserve `job.log` in the job directory during cleanup.
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
        # Remove steps not present in flow
        """
        Prune the current job directory to match the active flow and clean build directories for nodes marked as waiting.
        
        This method removes on-disk step directories that are not part of the current flow, removes index subdirectories within kept steps that are not present in the current flow, and for nodes whose status is waiting/pending invokes the node's runtime cleanup to clear its per-node build directory.
        """
        keep_steps = set([step for step, _ in self.__flow.get_nodes()])
        cur_job_dir = jobdir(self.__project)
        for step in os.listdir(cur_job_dir):
            if not os.path.isdir(os.path.join(cur_job_dir, step)):
                continue
            if step not in keep_steps:
                shutil.rmtree(os.path.join(cur_job_dir, step))
        for step in os.listdir(cur_job_dir):
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
        Prepare and configure all flow nodes before execution.
        
        Loads prior run manifests for nodes eligible to be reused, runs per-node setup, forwards preserved statuses, determines which successful nodes require rerun and marks their dependents as pending, replays preserved run information into the current project, handles a SchedulerFlowReset by forcing a full clean and marking all nodes pending, ensures any waiting or error nodes are marked pending, writes the resulting manifest for this job, and stops the run journal.
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
        Detect a headless Linux environment and set the project's `option.nodisplay` to True.
        
        If running on Linux and neither `DISPLAY` nor `WAYLAND_DISPLAY` is set in the environment,
        logs a warning and updates the project's `option.nodisplay` to True to prevent GUI usage.
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