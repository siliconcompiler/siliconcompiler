import json
import os
import shlex
import shutil
import stat
import subprocess
import uuid
import time

import os.path

from typing import List, Union, Final

from siliconcompiler import utils, sc_open
from siliconcompiler.utils.paths import jobdir
from siliconcompiler.package import RemoteResolver
from siliconcompiler.scheduler import SchedulerNode
from siliconcompiler.utils.logging import SCBlankLoggerFormatter
from siliconcompiler.utils.multiprocessing import MPManager


class SlurmSchedulerNode(SchedulerNode):
    """A SchedulerNode implementation for running tasks on a Slurm cluster.

    This class extends the base SchedulerNode to handle the specifics of
    submitting a compilation step as a job to a Slurm workload manager.
    It prepares a run script, a manifest, and uses the 'srun' command
    to execute the step on a compute node.
    """
    __OPTIONS: Final[str] = "scheduler-slurm"

    _MAX_FS_DELAY = 2
    _FS_DWELL = 0.1

    def __init__(self, project, step, index, replay=False):
        """Initializes a SlurmSchedulerNode.

        Args:
            project (Project): The parent project object.
            step (str): The step name in the flowgraph.
            index (str): The index for the step.
            replay (bool): If True, sets up the node to replay a previous run.
        """
        super().__init__(project, step, index, replay=replay)

        # Get the temporary UID associated with this job run.
        self.__job_hash = project.get('record', 'remoteid')
        if not self.__job_hash:
            # Generate a new uuid since it was not set
            self.__job_hash = uuid.uuid4().hex

    @property
    def jobhash(self):
        """str: A unique hash identifying the entire job run."""
        return self.__job_hash

    @staticmethod
    def init(project):
        """
        A static pre-processing hook for the Slurm scheduler.

        This method ensures that the Slurm environment is available and loads
        any existing user configuration for the scheduler.

        Args:
            project (Project): The project object to perform pre-processing on.
        """
        SlurmSchedulerNode.assert_slurm()

    @staticmethod
    def _set_user_config(tag: str, value: Union[List[str], str]) -> None:
        """
        Sets a specific value in the user configuration map.

        Args:
            tag (str): The configuration key to update.
            value (Union[List[str], str]): The value to assign to the key.
        """
        MPManager.get_settings().set(SlurmSchedulerNode.__OPTIONS, tag, value)

    @staticmethod
    def _write_user_config() -> None:
        """
        Writes the current system configuration to the user configuration file.
        """
        MPManager.get_settings().save()

    @property
    def is_local(self):
        """bool: Returns False, as this node executes on a remote cluster."""
        return False

    @staticmethod
    def get_configuration_directory(project):
        """Gets the directory for storing Slurm-related configuration files.

        Args:
            project (Project): The project object.

        Returns:
            str: The path to the configuration directory.
        """

        return os.path.join(jobdir(project), 'sc_configs')

    @staticmethod
    def get_job_name(jobhash, step, index):
        """Generates a unique job name for a Slurm job.

        Args:
            jobhash (str): The unique hash for the entire run.
            step (str): The step name of the node.
            index (str): The index of the node.

        Returns:
            str: A unique job name string.
        """
        return f'{jobhash}_{step}_{index}'

    @staticmethod
    def get_runtime_file_name(jobhash, step, index, ext):
        """Generates a standardized filename for runtime files.

        Args:
            jobhash (str): The unique hash for the entire run.
            step (str): The step name of the node.
            index (str): The index of the node.
            ext (str): The file extension.

        Returns:
            str: A standardized filename.
        """
        return f"{SlurmSchedulerNode.get_job_name(jobhash, step, index)}.{ext}"

    @staticmethod
    def get_slurm_partition():
        """Determines a default Slurm partition by querying the cluster.

        Returns:
            str: The name of the first available Slurm partition.

        Raises:
            RuntimeError: If the 'sinfo' command fails.
        """
        partitions = subprocess.run(['sinfo', '--json'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)

        if partitions.returncode != 0:
            raise RuntimeError('Unable to determine partitions in slurm')

        sinfo = json.loads(partitions.stdout.decode())

        # Return the first listed partition
        return sinfo['nodes'][0]['partitions'][0]

    @staticmethod
    def assert_slurm() -> None:
        """
        Check if slurm is installed and throw error when not installed.
        """
        if shutil.which('sinfo') is None:
            raise RuntimeError('slurm is not available or installed on this machine')

    def mark_copy(self) -> bool:
        sharedprefix: List[str] = MPManager.get_settings().get(
            SlurmSchedulerNode.__OPTIONS, "sharedpaths", default=[])

        if "/" in sharedprefix:
            # Entire filesystem is shared so no need to check
            return False

        do_collect = False
        for key in self.get_required_path_keys():
            mark_copy = True
            if sharedprefix:
                mark_copy = False

                check_step, check_index = self.step, self.index
                if self.project.get(*key, field='pernode').is_never():
                    check_step, check_index = None, None

                paths = self.project.find_files(*key, missing_ok=True,
                                                step=check_step, index=check_index)
                if not isinstance(paths, list):
                    paths = [paths]
                paths = [str(path) for path in paths if path]

                for path in paths:
                    if not any([path.startswith(shared) for shared in sharedprefix]):
                        # File exists outside shared paths and needs to be copied
                        mark_copy = True
                        break

            if mark_copy:
                self.project.set(*key, True, field='copy')
                do_collect = True
        return do_collect

    def run(self):
        """
        Runs the node's task as a job on a Slurm cluster.

        This method prepares all necessary files (manifest, run script),
        constructs an 'srun' command, and submits the job. It then blocks
        until the job completes on the compute node.
        """

        self._init_run_logger()

        # Determine which cluster parititon to use.
        partition = self.project.get('option', 'scheduler', 'queue',
                                     step=self.step, index=self.index)
        if not partition:
            partition = SlurmSchedulerNode.get_slurm_partition()

        # Write out the current schema for the compute node to pick up.
        cfg_dir = SlurmSchedulerNode.get_configuration_directory(self.project)
        os.makedirs(cfg_dir, exist_ok=True)

        cfg_file = os.path.join(cfg_dir, SlurmSchedulerNode.get_runtime_file_name(
            self.__job_hash, self.step, self.index, "pkg.json"))
        log_file = os.path.join(cfg_dir, SlurmSchedulerNode.get_runtime_file_name(
            self.__job_hash, self.step, self.index, "log"))
        script_file = os.path.join(cfg_dir, SlurmSchedulerNode.get_runtime_file_name(
            self.__job_hash, self.step, self.index, "sh"))

        # Remove scheduler as this is now a local run
        self.project.set('option', 'scheduler', 'name', None, step=self.step, index=self.index)
        self.project.write_manifest(cfg_file)

        # Allow user-defined compute node execution script if it already exists on the filesystem.
        # Otherwise, create a minimal script to run the task using the SiliconCompiler CLI.
        if not os.path.isfile(script_file):
            with open(script_file, 'w') as sf:
                sf.write(utils.get_file_template('slurm/run.sh').render(
                    cfg_file=shlex.quote(cfg_file),
                    build_dir=shlex.quote(self.project.option.get_builddir()),
                    step=shlex.quote(self.step),
                    index=shlex.quote(self.index),
                    cachedir=shlex.quote(str(RemoteResolver.determine_cache_dir(self.project)))
                ))

        # This is Python for: `chmod +x [script_path]`
        os.chmod(script_file,
                 os.stat(script_file).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        schedule_cmd = ['srun',
                        '--exclusive',
                        '--partition', partition,
                        '--chdir', self.project_cwd,
                        '--job-name', SlurmSchedulerNode.get_job_name(self.__job_hash,
                                                                      self.step, self.index),
                        '--output', log_file]

        # Only delay the starting time if the 'defer' Schema option is specified.
        defer_time = self.project.get('option', 'scheduler', 'defer',
                                      step=self.step, index=self.index)
        if defer_time:
            schedule_cmd.extend(['--begin', defer_time])

        schedule_cmd.append(script_file)

        self.logger.debug(f"Executing slurm command: {shlex.join(schedule_cmd)}")

        # Run the 'srun' command, and track its output.
        # TODO: output should be fed to log, and stdout if quiet = False
        step_result = subprocess.Popen(schedule_cmd,
                                       stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)

        # Wait for the subprocess call to complete. It should already be done,
        # as it has closed its output stream. But if we don't call '.wait()',
        # the '.returncode' value will not be set correctly.
        step_result.wait()

        # Attempt to list dir to trigger network FS to update
        try:
            os.listdir(os.path.dirname(log_file))
        except:  # noqa E722
            pass

        # Print the log to logger
        if os.path.exists(log_file):
            org_formatter = self.project._logger_console.formatter
            try:
                self.project._logger_console.setFormatter(SCBlankLoggerFormatter())
                with sc_open(log_file) as log:
                    for line in log.readlines():
                        self.logger.info(line.rstrip())
            finally:
                self.project._logger_console.setFormatter(org_formatter)

        if step_result.returncode != 0:
            self.logger.error(f"Slurm exited with a non-zero code ({step_result.returncode}).")
            if os.path.exists(log_file):
                self.logger.error(f"Node log file: {log_file}")
            self.halt()

        # Wait for manifest to propagate through network filesystem
        start = time.time()
        elapsed = 0
        manifest_path = self.get_manifest()
        while not os.path.exists(manifest_path) and elapsed <= SlurmSchedulerNode._MAX_FS_DELAY:
            os.listdir(os.path.dirname(manifest_path))
            elapsed = time.time() - start
            time.sleep(SlurmSchedulerNode._FS_DWELL)
        if not os.path.exists(manifest_path):
            self.logger.error(f"Manifest was not created on time: {manifest_path}")

    def check_required_paths(self) -> bool:
        return True
