import base64
import os
import shlex
import subprocess
import stat
import time

###########################################################################
def _deferstep(chip, step, index, status):
    '''
    Helper method to run an individual step on a slurm cluster.
    If a base64-encoded 'decrypt_key' is set in the Chip's status
    dictionary, the job's data is assumed to be encrypted,
    and a more complex command is assembled to ensure that the data
    is only decrypted temporarily in the compute node's local storage.
    '''

    # Determine which HPC job scheduler being used.
    scheduler_type = chip.get('option', 'scheduler', 'name', step=step, index=index)

    # Determine which cluster parititon to use. (Default value can be overridden on per-step basis)
    if f'{step}_slurm_partition' in chip.status:
        partition = chip.status[f'{step}_slurm_partition']
    else:
        partition = chip.status['slurm_partition']
    # Get the temporary UID associated with this job run.
    job_hash = chip.status['jobhash']

    # Job data is not encrypted, so it can be run in shared storage.
    # Write out the current schema for the compute node to pick up.
    job_dir = chip._getworkdir()
    cfg_dir = f'{job_dir}/configs'
    cfg_file = f'{cfg_dir}/{step}{index}.json'
    if not os.path.isdir(cfg_dir):
        os.mkdir(cfg_dir)
    chip.unset('option', 'scheduler', 'name', step=step, index=index)
    chip.write_manifest(cfg_file)

    if scheduler_type == 'slurm':
        # The script defining this Chip object may specify feature(s) to
        # ensure that the job runs on a specific subset of available nodes.
        if 'slurm_constraint' in chip.status:
            slurm_constraint = chip.status['slurm_constraint']
        else:
            slurm_constraint = 'SHARED'

        # Set the log file location.
        # TODO: May need to prepend ('option', 'builddir') and remove the '--chdir' arg if
        # running on a locally-managed cluster control node instead of submitting to a server app.
        #output_file = os.path.join(chip.get('option', 'builddir'),
        output_file = os.path.join(chip.get('design'),
                                   chip.get('option', 'jobname'),
                                   f'sc_remote-{step}-{index}.log')
        schedule_cmd = ['sbatch', '--exclusive',
                       '--constraint', slurm_constraint,
                       '--partition', partition,
                       '--chdir', chip.get('option', 'builddir'),
                       '--job-name', f'{job_hash}_{step}{index}',
                       '--output', output_file,
                       ]
        # Only specify an account if accounting is required for this cluster/run.
        if 'slurm_account' in chip.status:
            username = chip.status['slurm_account']
            schedule_cmd.extend(['--acount', username])
    elif scheduler_type == 'lsf':
        # TODO: LSF support is untested and currently unsupported.
        schedule_cmd = ['lsrun']

    # Create a command to defer execution to a compute node.
    script_path = f'{cfg_dir}/{step}{index}.sh'
    with open(script_path, 'w') as sf:
        sf.write('#!/bin/bash\n')
        sf.write(f'sc -cfg {shlex.quote(cfg_file)} -builddir {shlex.quote(chip.get("option", "builddir"))} '\
                    f'-arg_step {shlex.quote(step)} -arg_index {shlex.quote(index)} '\
                    f"-design {shlex.quote(chip.top())}\n")
        # In case of error(s) which prevents the SC build script from completing, ensure the
        # file mutex for job completion is set in shared storage. This lockfile signals the server
        # to mark the job done, without putting load on the cluster reporting/accounting system.
        sf.write(f'touch {os.path.dirname(output_file)}/done')

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
                                         '--partition', 'debug',
                                         '--name', f'{job_hash}_{step}{index}',
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

        # With native autoscaling, job can be 'PENDING', 'CONFIGURING', or 'COMPLETING'
        # while the scale-up/down scripts are running.
        if ('RUNNING' in jobout) or ('PENDING' in jobout) or ('CONFIGURING' in jobout) or ('COMPLETING' in jobout):
            if 'watchdog' in chip.status:
                chip.status['watchdog'].set()
        elif 'COMPLETED' in jobout:
            break
        elif 'Invalid job id specified' in jobout:
            # May have already completed and been purged from active list.
            break
        else:
            # FAILED, etc.
            retcode = 1
            break

    if retcode > 0:
        chip.logger.error(f'srun command for {step} failed.')
