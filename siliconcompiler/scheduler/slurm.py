import os
import shlex
import subprocess
import stat
import uuid
import json
import shutil

import os.path

from siliconcompiler import utils
from siliconcompiler.package import RemoteResolver
from siliconcompiler.flowgraph import RuntimeFlowgraph
from siliconcompiler.scheduler.schedulernode import SchedulerNode


class SlurmSchedulerNode(SchedulerNode):
    def __init__(self, chip, step, index, replay=False):
        super().__init__(chip, step, index, replay=replay)

        # Get the temporary UID associated with this job run.
        self.__job_hash = chip.get('record', 'remoteid')
        if not self.__job_hash:
            # Generate a new uuid since it was not set
            self.__job_hash = uuid.uuid4().hex

    @property
    def jobhash(self):
        return self.__job_hash

    @staticmethod
    def init(chip):
        if os.path.exists(chip._getcollectdir()):
            # nothing to do
            return

        collect = False
        flow = chip.get('option', 'flow')
        entry_nodes = chip.get("flowgraph", flow, field="schema").get_entry_nodes()

        runtime = RuntimeFlowgraph(
            chip.get("flowgraph", flow, field='schema'),
            from_steps=chip.get('option', 'from'),
            to_steps=chip.get('option', 'to'),
            prune_nodes=chip.get('option', 'prune'))

        for (step, index) in runtime.get_nodes():
            if (step, index) in entry_nodes:
                collect = True

        if collect:
            chip.collect()

    @property
    def is_local(self):
        return False

    @staticmethod
    def get_configuration_directory(chip):
        '''
        Helper function to get the configuration directory for the scheduler
        '''

        return os.path.join(chip.getworkdir(), 'sc_configs')

    @staticmethod
    def get_job_name(jobhash, step, index):
        return f'{jobhash}_{step}_{index}'

    @staticmethod
    def get_runtime_file_name(jobhash, step, index, ext):
        return f"{SlurmSchedulerNode.get_job_name(jobhash, step, index)}.{ext}"

    @staticmethod
    def get_slurm_partition():
        partitions = subprocess.run(['sinfo', '--json'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)

        if partitions.returncode != 0:
            raise RuntimeError('Unable to determine partitions in slurm')

        sinfo = json.loads(partitions.stdout.decode())

        # Return the first listed partition
        return sinfo['nodes'][0]['partitions'][0]

    def run(self):
        '''
        Helper method to run an individual step on a slurm cluster.

        Blocks until the compute node
        finishes processing this step, and it sets the active/error bits.
        '''

        self._init_run_logger()

        if shutil.which('sinfo') is None:
            raise RuntimeError('slurm is not available or installed on this machine')

        # Determine which cluster parititon to use.
        partition = self.chip.get('option', 'scheduler', 'queue', step=self.step, index=self.index)
        if not partition:
            partition = SlurmSchedulerNode.get_slurm_partition()

        # Write out the current schema for the compute node to pick up.
        cfg_dir = SlurmSchedulerNode.get_configuration_directory(self.chip)
        os.makedirs(cfg_dir, exist_ok=True)

        cfg_file = os.path.join(cfg_dir, SlurmSchedulerNode.get_runtime_file_name(
            self.__job_hash, self.step, self.index, "pkg.json"))
        log_file = os.path.join(cfg_dir, SlurmSchedulerNode.get_runtime_file_name(
            self.__job_hash, self.step, self.index, "log"))
        script_file = os.path.join(cfg_dir, SlurmSchedulerNode.get_runtime_file_name(
            self.__job_hash, self.step, self.index, "sh"))

        # Remove scheduler as this is now a local run
        self.chip.set('option', 'scheduler', 'name', None, step=self.step, index=self.index)
        self.chip.write_manifest(cfg_file)

        # Allow user-defined compute node execution script if it already exists on the filesystem.
        # Otherwise, create a minimal script to run the task using the SiliconCompiler CLI.
        if not os.path.isfile(script_file):
            with open(script_file, 'w') as sf:
                sf.write(utils.get_file_template('slurm/run.sh').render(
                    cfg_file=shlex.quote(cfg_file),
                    build_dir=shlex.quote(self.chip.get("option", "builddir")),
                    step=shlex.quote(self.step),
                    index=shlex.quote(self.index),
                    cachedir=shlex.quote(str(RemoteResolver.determine_cache_dir(self.chip)))
                ))

        # This is Python for: `chmod +x [script_path]`
        os.chmod(script_file,
                 os.stat(script_file).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        schedule_cmd = ['srun',
                        '--exclusive',
                        '--partition', partition,
                        '--chdir', self.chip.cwd,
                        '--job-name', SlurmSchedulerNode.get_job_name(self.__job_hash,
                                                                      self.step, self.index),
                        '--output', log_file]

        # Only delay the starting time if the 'defer' Schema option is specified.
        defer_time = self.chip.get('option', 'scheduler', 'defer', step=self.step, index=self.index)
        if defer_time:
            schedule_cmd.extend(['--begin', defer_time])

        schedule_cmd.append(script_file)

        # Run the 'srun' command, and track its output.
        # TODO: output should be fed to log, and stdout if quiet = False
        step_result = subprocess.Popen(schedule_cmd,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)

        # Wait for the subprocess call to complete. It should already be done,
        # as it has closed its output stream. But if we don't call '.wait()',
        # the '.returncode' value will not be set correctly.
        step_result.wait()
