import os
import shlex
import subprocess
import stat
import time
import uuid
import json

# Full list of Slurm states, split into 'active' and 'inactive' categories.
# Many of these do not apply to a minimal configuration, but we'll track them all.
# https://slurm.schedmd.com/squeue.html#SECTION_JOB-STATE-CODES
SLURM_ACTIVE_STATES = [
    'RUNNING',
    'PENDING',
    'CONFIGURING',
    'COMPLETING',
    'SIGNALING',
    'STAGE_OUT',
    'RESIZING',
    'REQUEUED',
]
SLURM_INACTIVE_STATES = [
    'BOOT_FAIL',
    'CANCELLED',
    'COMPLETED',
    'DEADLINE',
    'FAILED',
    'NODE_FAIL',
    'OUT_OF_MEMORY',
    'PREEMPTED',
    'RESV_DEL_HOLD',
    'REQUEUE_FED',
    'REQUEUE_HOLD',
    'REVOKED',
    'SPECIAL_EXIT',
    'STOPPED',
    'SUSPENDED',
    'TIMEOUT',
]


###########################################################################
def _defernode(chip, step, index):
    '''
    Helper method to run an individual step on a slurm cluster.

    Blocks until the compute node
    finishes processing this step, and it sets the active/error bits.
    '''

    # Determine which HPC job scheduler being used.
    scheduler_type = chip.get('option', 'scheduler', 'name', step=step, index=index)

    if scheduler_type != 'slurm':
        raise ValueError(f'{scheduler_type} is not a supported scheduler')

    # Determine which cluster parititon to use. (Default value can be overridden on per-step basis)
    partition = chip.get('option', 'scheduler', 'queue', step=step, index=index)
    if not partition:
        partition = _get_slurm_partition()

    # Get the temporary UID associated with this job run.
    job_hash = chip.get('record', 'remoteid')
    if not job_hash:
        # Generate a new uuid since it was not set
        job_hash = uuid.uuid4().hex

    job_name = f'{job_hash}_{step}{index}'

    # Write out the current schema for the compute node to pick up.
    job_dir = chip._getworkdir()
    cfg_dir = f'{job_dir}/configs'
    cfg_file = f'{cfg_dir}/{step}{index}.json'
    os.makedirs(cfg_dir, exist_ok=True)

    chip.set('option', 'scheduler', 'name', None, step=step, index=index)
    chip.write_manifest(cfg_file)

    # Set the log file location.
    # TODO: May need to prepend ('option', 'builddir') and remove the '--chdir' arg if
    # running on a locally-managed cluster control node instead of submitting to a server app.
    output_file = os.path.join(chip._getworkdir(),
                               f'sc_remote-{step}-{index}.log')
    schedule_cmd = ['sbatch',
                    '--exclusive',
                    '--partition', partition,
                    '--chdir', chip.cwd,
                    '--job-name', job_name,
                    '--output', output_file]

    # The script defining this Chip object may specify feature(s) to
    # ensure that the job runs on a specific subset of available nodes.
    # TODO: Maybe we should add a Schema parameter for these values.
    if 'slurm_constraint' in chip.status:
        schedule_cmd.extend(['--constraint', chip.status['slurm_constraint']])

    # Only specify an account if accounting is required for this cluster/run.
    if 'slurm_account' in chip.status:
        schedule_cmd.extend(['--account', chip.status['slurm_account']])

    # Only delay the starting time if the 'defer' Schema option is specified.
    defer_time = chip.get('option', 'scheduler', 'defer', step=step, index=index)
    if defer_time:
        schedule_cmd.extend(['--begin', defer_time])

    # Allow user-defined compute node execution script if it already exists on the filesystem.
    # Otherwise, create a minimal script to run the task using the SiliconCompiler CLI.
    script_path = f'{cfg_dir}/{step}{index}.sh'
    buildir = chip.get("option", "builddir")
    if not os.path.isfile(script_path):
        with open(script_path, 'w') as sf:
            sf.write('#!/bin/bash\n')
            sf.write(f'sc -cfg {shlex.quote(cfg_file)} -builddir {shlex.quote(buildir)} '
                     f'-arg_step {shlex.quote(step)} -arg_index {shlex.quote(index)}\n')

    # This is Python for: `chmod +x [script_path]`
    fst = os.stat(script_path)
    os.chmod(script_path, fst.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    schedule_cmd.append(script_path)

    # Run the 'srun' command, and track its output.
    # TODO: output should be fed to log, and stdout if quiet = False
    step_result = subprocess.Popen(schedule_cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)

    # Wait for the subprocess call to complete. It should already be done,
    # as it has closed its output stream. But if we don't call '.wait()',
    # the '.returncode' value will not be set correctly.
    step_result.wait()
    result_msg = step_result.stdout.read().decode()
    sbatch_id = result_msg.split(' ')[-1].strip()
    retcode = 0

    while True:
        # Return early with an error if the batch ID is not an integer.
        if not sbatch_id.isdigit():
            retcode = 1
            break

        # Rate-limit the status checks to once every few seconds.
        time.sleep(3.0)

        # If a maximum disk space was defined, ensure that it is respected.
        if 'max_fs_bytes' in chip.status:
            du_cmd = subprocess.run(['du', '-sb', chip.get('option', 'builddir')],
                                    stdout=subprocess.PIPE)
            cur_fs_bytes = int(du_cmd.stdout.decode().split()[0])
            if cur_fs_bytes > int(chip.status['max_fs_bytes']):
                # File size overrun; cancel the current task, and mark an error.
                retcode = 1
                sq_out = subprocess.run(['squeue',
                                         '--partition', partition,
                                         '--name', job_name,
                                         '--noheader'],
                                        stdout=subprocess.PIPE)
                for line in sq_out.stdout.splitlines():
                    subprocess.run(['sudo', 'scancel', line.split()[0]])
                break

        # Check whether the job is still running.
        jobcheck = subprocess.run(['scontrol', 'show', 'job', sbatch_id],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)
        jobout = jobcheck.stdout.decode()

        # Jobs have a number of potential states that they can be in if they
        # are still active in the Slurm scheduler.
        if [state for state in SLURM_ACTIVE_STATES if state in jobout]:
            if 'watchdog' in chip.status:
                chip.status['watchdog'].set()
        # 'COMPLETED' is a special case indicating successful job termination.
        elif 'COMPLETED' in jobout:
            break
        elif 'Invalid job id specified' in jobout:
            # May have already completed and been purged from active list.
            break
        # Jobs have a number of potential states that they can be in if they
        # did not terminate successfully.
        elif [state for state in SLURM_INACTIVE_STATES if state in jobout]:
            # FAILED, TIMEOUT, etc.
            retcode = 1
            break

    if retcode > 0:
        chip.logger.error(f'srun command for {step} failed.')
        chip.logger.error(f'srun output for {step}:\n{jobout}')


def _get_slurm_partition():
    partitions = subprocess.run(['sinfo', '--json'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    if partitions.returncode != 0:
        raise RuntimeError('Unable to determine partitions in slurm')

    sinfo = json.loads(partitions.stdout.decode())

    # Return the first listed partition
    return sinfo['nodes'][0]['partitions'][0]
