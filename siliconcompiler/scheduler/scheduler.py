import os
import re
import shutil
import sys

import os.path

from siliconcompiler import Schema
from siliconcompiler import NodeStatus
from siliconcompiler.schema import Journal
from siliconcompiler.flowgraph import RuntimeFlowgraph
from siliconcompiler.scheduler.schedulernode import SchedulerNode
from siliconcompiler.scheduler.slurm import SlurmSchedulerNode
from siliconcompiler.scheduler.docker import DockerSchedulerNode
from siliconcompiler.scheduler.taskscheduler import TaskScheduler

from siliconcompiler import utils
from siliconcompiler.scheduler import send_messages


class Scheduler:
    def __init__(self, chip):
        self.__chip = chip
        self.__logger = self.__chip.logger

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
            raise ValueError(f"{self.__flow.name()} flowgraph contains errors and cannot be run.")
        if not RuntimeFlowgraph.validate(
                self.__flow,
                from_steps=from_steps,
                to_steps=to_steps,
                prune_nodes=prune_nodes,
                logger=chip.logger):
            raise ValueError(f"{self.__flow.name()} flowgraph contains errors and cannot be run.")

        self.__flow_runtime = RuntimeFlowgraph(
            self.__flow,
            from_steps=from_steps,
            to_steps=to_steps,
            prune_nodes=self.__chip.get('option', 'prune'))

        self.__flow_runtime_no_prune = RuntimeFlowgraph(
            self.__flow,
            from_steps=from_steps,
            to_steps=to_steps)

        self.__flow_load_runtime = RuntimeFlowgraph(
            self.__flow,
            to_steps=from_steps,
            prune_nodes=prune_nodes)

        self.__flow_something = RuntimeFlowgraph(
            self.__flow,
            from_steps=set([step for step, _ in self.__flow.get_entry_nodes()]),
            prune_nodes=prune_nodes)

        self.__record = self.__chip.get("record", field="schema")
        self.__metrics = self.__chip.get("metric", field="schema")

        self.__tasks = {}

    def __print_status(self, header):
        self.__logger.debug(f"#### {header}")
        for step, index in self.__flow.get_nodes():
            self.__logger.debug(f"({step}, {index}) -> "
                                f"{self.__record.get('status', step=step, index=index)}")
        self.__logger.debug("####")

    def check_manifest(self):
        self.__logger.info("Checking manifest before running.")
        return self.__chip.check_manifest()

    def run_core(self):
        self.__record.record_python_packages()

        task_scheduler = TaskScheduler(self.__chip, self.__tasks)
        task_scheduler.run()
        task_scheduler.check()

    def run(self):
        self.__run_setup()
        self.configure_nodes()

        # Check validity of setup
        if not self.check_manifest():
            raise RuntimeError("check_manifest() failed")

        self.run_core()

        # Store run in history
        self.__chip.schema.record_history()

        # Record final manifest
        filepath = os.path.join(self.__chip.getworkdir(), f"{self.__chip.design}.pkg.json")
        self.__chip.write_manifest(filepath)

        send_messages.send(self.__chip, 'summary', None, None)

    def __mark_pending(self, step, index):
        if (step, index) not in self.__flow_runtime.get_nodes():
            return

        self.__record.set('status', NodeStatus.PENDING, step=step, index=index)
        for next_step, next_index in self.__flow_runtime.get_nodes_starting_at(step, index):
            if self.__record.get('status', step=next_step, index=next_index) == NodeStatus.SKIPPED:
                continue

            # Mark following steps as pending
            self.__record.set('status', NodeStatus.PENDING, step=next_step, index=next_index)

    def __run_setup(self):
        self.__check_display()

        org_jobname = self.__chip.get('option', 'jobname')
        copy_prev_job = self.__increment_job_name()

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

            if copy_prev_job and (step, index) in copy_from_nodes:
                self.__tasks[(step, index)].copy_from(org_jobname)

        if copy_prev_job:
            # Copy collection directory
            copy_from = self.__chip._getcollectdir(jobname=org_jobname)
            copy_to = self.__chip._getcollectdir()
            if os.path.exists(copy_from):
                shutil.copytree(copy_from, copy_to,
                                dirs_exist_ok=True,
                                copy_function=utils.link_copy)

        self.__clean_build_dir()
        self.__reset_flow_nodes()

    def __reset_flow_nodes(self):
        # Reset record
        for step, index in self.__flow.get_nodes():
            self.__record.clear(step, index, keep=['remoteid', 'status', 'pythonpackage'])
            self.__record.set('status', NodeStatus.PENDING, step=step, index=index)

        # Reset metrics
        for step, index in self.__flow.get_nodes():
            self.__metrics.clear(step, index)

    def __clean_build_dir(self):
        if self.__record.get('remoteid'):
            return

        if self.__chip.get('option', 'clean') and not self.__chip.get('option', 'from'):
            # If no step or nodes to start from were specified, the whole flow is being run
            # start-to-finish. Delete the build dir to clear stale results.
            cur_job_dir = self.__chip.getworkdir()
            if os.path.isdir(cur_job_dir):
                shutil.rmtree(cur_job_dir)

    def configure_nodes(self):
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
                                    f'{self.__chip.design}.pkg.json')
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

        self.__chip.write_manifest(os.path.join(self.__chip.getworkdir(),
                                                f"{self.__chip.get('design')}.pkg.json"))
        journal.stop()

        # Clean nodes marked pending
        for step, index in self.__flow_runtime.get_nodes():
            if NodeStatus.is_waiting(self.__record.get('status', step=step, index=index)):
                with self.__tasks[(step, index)].runtime():
                    self.__tasks[(step, index)].clean_directory()

    def __check_display(self):
        '''
        Automatically disable display for Linux systems without desktop environment
        '''

        if not self.__chip.get('option', 'nodisplay') and sys.platform == 'linux' \
                and 'DISPLAY' not in os.environ and 'WAYLAND_DISPLAY' not in os.environ:
            self.__logger.warning('Environment variable $DISPLAY or $WAYLAND_DISPLAY not set')
            self.__logger.warning("Setting [option,nodisplay] to True")
            self.__chip.set('option', 'nodisplay', True)

    def __increment_job_name(self):
        '''
        Auto-update jobname if [option,jobincr] is True
        Do this before initializing logger so that it picks up correct jobname
        '''

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
