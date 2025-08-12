import io
import logging
import os
import re
import shutil
import sys
import traceback

import os.path

from siliconcompiler import Schema
from siliconcompiler import NodeStatus
from siliconcompiler.schema import Journal
from siliconcompiler.flowgraph import RuntimeFlowgraph
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.scheduler import SlurmSchedulerNode
from siliconcompiler.scheduler import DockerSchedulerNode
from siliconcompiler.scheduler import TaskScheduler

from siliconcompiler import utils
from siliconcompiler.utils.logging import SCLoggerFormatter
from siliconcompiler.utils.multiprocessing import MPManager
from siliconcompiler.scheduler import send_messages


class Scheduler:
    """
    A class for orchestrating and executing a compilation flowgraph.

    The Scheduler is responsible for managing the entire lifecycle of a compilation
    run. It interprets the flowgraph defined in the Chip object, determines which
    nodes (steps) need to be run based on user settings (like 'from', 'to') and
    the state of previous runs, and then executes the tasks in the correct order.

    It handles setting up individual task nodes, managing dependencies, logging,
    and reporting results.
    """

    def __init__(self, chip):
        """
        Initializes the Scheduler.

        Args:
            chip (Chip): The Chip object containing the configuration and flowgraph.

        Raises:
            ValueError: If the specified flow is not defined or fails validation.
        """
        self.__chip = chip
        self.__logger: logging.Logger = chip.logger
        self.__name = chip.design

        flow = self.__chip.get("option", "flow")
        if not flow:
            raise ValueError("flow must be specified")

        if flow not in self.__chip.getkeys("flowgraph"):
            raise ValueError("flow is not defined")

        self.__flow = self.__chip.get("flowgraph", flow, field="schema")
        from_steps = self.__chip.get('option', 'from')
        to_steps = self.__chip.get('option', 'to')
        prune_nodes = self.__chip.get('option', 'prune')

        if not self.__flow.validate(logger=self.__logger):
            raise ValueError(f"{self.__flow.name} flowgraph contains errors and cannot be run.")
        if not RuntimeFlowgraph.validate(
                self.__flow,
                from_steps=from_steps,
                to_steps=to_steps,
                prune_nodes=prune_nodes,
                logger=chip.logger):
            raise ValueError(f"{self.__flow.name} flowgraph contains errors and cannot be run.")

        self.__flow_runtime = RuntimeFlowgraph(
            self.__flow,
            from_steps=from_steps,
            to_steps=to_steps,
            prune_nodes=self.__chip.get('option', 'prune'))

        self.__flow_load_runtime = RuntimeFlowgraph(
            self.__flow,
            to_steps=from_steps,
            prune_nodes=prune_nodes)

        self.__record = self.__chip.get("record", field="schema")
        self.__metrics = self.__chip.get("metric", field="schema")

        self.__tasks = {}

        # Create dummy handler
        self.__joblog_handler = logging.NullHandler()
        self.__org_job_name = self.__chip.get("option", "jobname")

    @property
    def project(self):
        """
        Returns the Project object associated with this scheduler.

        This property provides access to the central Project object, which holds
        the entire design configuration, flowgraph, and results.

        Returns:
            Project: The Project object for the current project.
        """
        return self.__chip

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
        Checks the validity of the Chip's manifest before a run.

        Returns:
            bool: True if the manifest is valid, False otherwise.
        """
        self.__logger.info("Checking manifest before running.")
        return self.__chip.check_manifest()

    def run_core(self):
        """
        Executes the core task scheduling loop.

        This method initializes and runs the TaskScheduler, which manages the
        execution of individual nodes based on their dependencies and status.
        """
        self.__record.record_python_packages()

        task_scheduler = TaskScheduler(self.__chip, self.__tasks)
        task_scheduler.run(self.__joblog_handler)
        task_scheduler.check()

    def __excepthook(self, exc_type, exc_value, exc_traceback):
        """
        Custom exception hook to ensure all fatal errors are logged.

        This captures unhandled exceptions, logs them to the job log file,
        and prints a traceback for debugging before the program terminates.
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
        if self.__chip._dash:
            self.__chip._dash.stop()

        # Mark error to keep logfile
        MPManager.error("uncaught exception")

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

        # Determine job name first so we can create a log
        if not self.__increment_job_name():
            # No need to copy, no remove org job name
            self.__org_job_name = None

        # Clean the directory early if needed
        self.__clean_build_dir()

        # Install job file logger
        os.makedirs(self.__chip.getworkdir(), exist_ok=True)
        file_log = os.path.join(self.__chip.getworkdir(), "job.log")
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

        # Configure run
        self.__chip._init_run()

        self.__run_setup()
        self.configure_nodes()

        # Check validity of setup
        if not self.check_manifest():
            raise RuntimeError("check_manifest() failed")

        # Check validity of flowgraphs IO
        if not self.__check_flowgraph_io():
            raise RuntimeError("Flowgraph file IO constrains errors")

        self.run_core()

        # Store run in history
        self.__chip.schema.record_history()

        # Record final manifest
        filepath = os.path.join(self.__chip.getworkdir(), f"{self.__name}.pkg.json")
        self.__chip.write_manifest(filepath)

        send_messages.send(self.__chip, 'summary', None, None)

        self.__logger.removeHandler(self.__joblog_handler)
        self.__joblog_handler = logging.NullHandler()

        # Restore hook
        sys.excepthook = org_excepthook

    def __check_flowgraph_io(self):
        '''Check if flowgraph is valid in terms of input and output files.

        Returns True if valid, False otherwise.
        '''
        nodes = self.__flow_runtime.get_nodes()

        for (step, index) in nodes:
            # Get files we receive from input nodes.
            in_nodes = self.__flow_runtime.get_node_inputs(step, index, record=self.__record)
            all_inputs = set()
            tool = self.__flow_runtime.get(step, index, "tool")
            task = self.__flow_runtime.get(step, index, "task")
            requirements = self.__chip.get("tool", tool, 'task', task, 'input',
                                           step=step, index=index)
            for in_step, in_index in in_nodes:
                if (in_step, in_index) not in nodes:
                    # If we're not running the input step, the required
                    # inputs need to already be copied into the build
                    # directory.
                    workdir = self.__chip.getworkdir(step=in_step, index=in_index)
                    in_step_out_dir = os.path.join(workdir, 'outputs')

                    if not os.path.isdir(in_step_out_dir):
                        # This means this step hasn't been run, but that
                        # will be flagged by a different check. No error
                        # message here since it would be redundant.
                        inputs = []
                        continue

                    design = self.__chip.get("option", 'design')
                    manifest = f'{design}.pkg.json'
                    inputs = [inp for inp in os.listdir(in_step_out_dir) if inp != manifest]
                else:
                    in_tool = self.__flow_runtime.get(in_step, in_index, "tool")
                    in_task = self.__flow_runtime.get(in_step, in_index, "task")
                    in_task_class = self.__chip.get("tool", in_tool, "task", in_task,
                                                    field="schema")

                    with in_task_class.runtime(SchedulerNode(self.__chip,
                                                             in_step, in_index)) as task:
                        inputs = task.get_output_files()

                task_class = self.__chip.get("tool", tool, "task", task, field="schema")
                with task_class.runtime(SchedulerNode(self.__chip,
                                                      step, index)) as task:
                    for inp in inputs:
                        node_inp = task.compute_input_file_node_name(inp, in_step, in_index)
                        if node_inp in requirements:
                            inp = node_inp
                        if inp in all_inputs:
                            self.__logger.error(f'Invalid flow: {step}/{index} '
                                                f'receives {inp} from multiple input tasks')
                            return False
                        all_inputs.add(inp)

            for requirement in requirements:
                if requirement not in all_inputs:
                    self.__logger.error(f'Invalid flow: {step}/{index} will '
                                        f'not receive required input {requirement}.')
                    return False

        return True

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

            node_scheduler = self.__chip.get('option', 'scheduler', 'name', step=step, index=index)
            if node_scheduler == 'slurm':
                node_cls = SlurmSchedulerNode
            elif node_scheduler == 'docker':
                node_cls = DockerSchedulerNode
            self.__tasks[(step, index)] = node_cls(self.__chip, step, index)
            if self.__flow.get(step, index, "tool") == "builtin":
                self.__tasks[(step, index)].set_builtin()

            if self.__org_job_name and (step, index) in copy_from_nodes:
                self.__tasks[(step, index)].copy_from(self.__org_job_name)

        if self.__org_job_name:
            # Copy collection directory
            copy_from = self.__chip._getcollectdir(jobname=self.__org_job_name)
            copy_to = self.__chip._getcollectdir()
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

    def __clean_build_dir(self):
        """
        Private helper to clean the build directory if necessary.

        If ['option', 'clean'] is True and the run starts from the beginning,
        the entire build directory is removed to ensure a fresh start.
        """
        if self.__record.get('remoteid'):
            return

        if self.__chip.get('option', 'clean') and not self.__chip.get('option', 'from'):
            # If no step or nodes to start from were specified, the whole flow is being run
            # start-to-finish. Delete the build dir to clear stale results.
            cur_job_dir = self.__chip.getworkdir()
            if os.path.isdir(cur_job_dir):
                shutil.rmtree(cur_job_dir)

    def configure_nodes(self):
        """
        Configures all nodes before execution.

        This is a critical step that determines the final state of each node
        (SUCCESS, PENDING, SKIPPED) before the scheduler starts. It loads
        results from previous runs, checks for any modifications to parameters
        or input files, and marks nodes for re-run accordingly.
        """
        from_nodes = []
        extra_setup_nodes = {}

        journal = Journal.access(self.__chip.schema)
        journal.start()

        self.__print_status("Start")

        if self.__chip.get('option', 'clean'):
            if self.__chip.get("option", "from"):
                from_nodes = self.__flow_runtime.get_entry_nodes()
            load_nodes = self.__flow.get_nodes()
        else:
            if self.__chip.get("option", "from"):
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

            manifest = os.path.join(self.__chip.getworkdir(step=step, index=index),
                                    'outputs',
                                    f'{self.__name}.pkg.json')
            if os.path.exists(manifest):
                # ensure we setup these nodes again
                try:
                    extra_setup_nodes[(step, index)] = Schema.from_manifest(filepath=manifest)
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
                        Journal.access(extra_setup_nodes[(step, index)]).replay(self.__chip.schema)

        self.__print_status("After requires run")

        # Ensure all nodes are marked as pending if needed
        for layer_nodes in self.__flow_runtime.get_execution_order():
            for step, index in layer_nodes:
                status = self.__record.get("status", step=step, index=index)
                if NodeStatus.is_waiting(status) or NodeStatus.is_error(status):
                    self.__mark_pending(step, index)

        self.__print_status("After ensure")

        os.makedirs(self.__chip.getworkdir(), exist_ok=True)
        self.__chip.write_manifest(os.path.join(self.__chip.getworkdir(),
                                                f"{self.__name}.pkg.json"))
        journal.stop()

        # Clean nodes marked pending
        for step, index in self.__flow_runtime.get_nodes():
            if NodeStatus.is_waiting(self.__record.get('status', step=step, index=index)):
                with self.__tasks[(step, index)].runtime():
                    self.__tasks[(step, index)].clean_directory()

    def __check_display(self):
        """
        Private helper to automatically disable GUI display on headless systems.

        If running on Linux without a DISPLAY or WAYLAND_DISPLAY environment
        variable, this sets ['option', 'nodisplay'] to True to prevent tools
        from attempting to open a GUI.
        """

        if not self.__chip.get('option', 'nodisplay') and sys.platform == 'linux' \
                and 'DISPLAY' not in os.environ and 'WAYLAND_DISPLAY' not in os.environ:
            self.__logger.warning('Environment variable $DISPLAY or $WAYLAND_DISPLAY not set')
            self.__logger.warning("Setting [option,nodisplay] to True")
            self.__chip.set('option', 'nodisplay', True)

    def __increment_job_name(self):
        """
        Private helper to auto-increment the jobname if ['option', 'jobincr'] is True.

        This prevents overwriting previous job results by finding the highest
        numbered existing job directory and creating a new one with an
        incremented number.

        Returns:
            bool: True if the job name was incremented, False otherwise.
        """
        if not self.__chip.get('option', 'clean'):
            return False
        if not self.__chip.get('option', 'jobincr'):
            return False

        workdir = self.__chip.getworkdir()
        if os.path.isdir(workdir):
            # Strip off digits following jobname, if any
            stem = self.__chip.get('option', 'jobname').rstrip('0123456789')

            dir_check = re.compile(fr'{stem}(\d+)')

            jobid = 0
            for job in os.listdir(os.path.dirname(workdir)):
                m = dir_check.match(job)
                if m:
                    jobid = max(jobid, int(m.group(1)))
            self.__chip.set('option', 'jobname', f'{stem}{jobid + 1}')
            return True
        return False
