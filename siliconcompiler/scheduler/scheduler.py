import os
import re
import sys

import os.path

from siliconcompiler.flowgraph import RuntimeFlowgraph


class Scheduler:
    def __init__(self, chip):
        self.__chip = chip

        flow = self.__chip.get("option", "flow")
        if not flow:
            raise ValueError

        if flow not in self.__chip.getkeys("flowgraph"):
            raise ValueError

        self.__flow = self.__chip.schema.get("flowgraph", flow, field="schema")
        from_steps = self.__chip.get('option', 'from')
        to_steps = self.__chip.get('option', 'to')
        prune_nodes = self.__chip.get('option', 'prune')

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

        self.__record = self.__chip.schema.get("record", flow, field="schema")

        self.__tasks = {}

    def run(self):
        pass

    def __run_setup(self):
        self._check_display()
        org_jobname = self.__chip.get('option', 'jobname')
        if self._increment_job_name():
            copy_old_run_dir(chip, org_jobname)
        clean_build_dir(chip)
        _reset_flow_nodes(chip, flow, runtime.get_nodes())

    def _check_display(self):
        '''
        Automatically disable display for Linux systems without desktop environment
        '''

        if not self.__chip.get('option', 'nodisplay') and sys.platform == 'linux' \
                and 'DISPLAY' not in os.environ and 'WAYLAND_DISPLAY' not in os.environ:
            self.__logger.warning('Environment variable $DISPLAY or $WAYLAND_DISPLAY not set')
            self.__logger.warning("Setting [option,nodisplay] to True")
            self.__chip.set('option', 'nodisplay', True)

    def _increment_job_name(self):
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
