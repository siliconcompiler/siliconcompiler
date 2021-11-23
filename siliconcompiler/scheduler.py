import base64
import os
import subprocess

###########################################################################
def _deferstep(chip, step, index, active, error):
    '''
    Helper method to run an individual step on a slurm cluster.
    If a base64-encoded 'decrypt_key' is set in the Chip's status
    dictionary, the job's data is assumed to be encrypted,
    and a more complex command is assembled to ensure that the data
    is only decrypted temporarily in the compute node's local storage.
    '''

    # Ensure that error bits are up-to-date in this schema.
    for in_step, in_index in chip.get('flowgraph', step, index, 'input'):
        #TODO: Why is this needed?
        chip.set('flowstatus', in_step, in_index, 'error', error[f'{in_step}{in_index}'])

    # Determine which HPC job scheduler being used.
    scheduler_type = chip.get('jobscheduler')
    username = chip.status['slurm_account']
    partition = chip.status['slurm_partition']
    job_hash = chip.status['jobhash']
    if scheduler_type == 'slurm':
        # The script defining this Chip object may specify feature(s) to
        # ensure that the job runs on a specific subset of available nodes.
        if 'slurm_constraint' in chip.status:
            slurm_constraint = chip.status['slurm_constraint']
        else:
            slurm_constraint = 'SHARED'
        schedule_cmd = f'sbatch --exclusive '\
                       f'--constraint {slurm_constraint} '\
                       f'--account "{username}" '\
                       f'--partition {partition} '\
                       f'--chdir {chip.get("dir")} '\
                       f'--job-name "{job_hash}_{step}{index}"'
    elif scheduler_type == 'lsf':
        # TODO: LSF support is untested and currently unsupported.
        schedule_cmd = 'lsrun'

    if 'decrypt_key' in chip.status:
        # Job data is encrypted, and it should only be decrypted in the
        # compute node's local storage.
        job_nameid = f"{chip.get('jobname')}"
        cur_build_dir = f"{chip.get('dir')}/{chip.get('design')}/{job_nameid}"
        tmp_job_dir = f"/tmp/{job_hash}"
        ctrl_node_dir = chip.get('dir')
        chip.set('dir', tmp_job_dir, clobber=True)
        tmp_build_dir = "/".join([tmp_job_dir,
                                  chip.get('design'),
                                  job_nameid])
        key_bytes = base64.urlsafe_b64decode(chip.status['decrypt_key'])
        keystr = key_bytes.decode()
        keypath = f"{tmp_job_dir}/dk"

        # Write the current schema out to an encrypted file in shared storage.
        write_encrypted_cfgfile(chip._prune(chip.cfg), cur_build_dir, key_bytes, f'{step}{index}')

        # Assemble a command to re-mount shared storage if necessary.
        # If the cluster uses NFS, rapid client connect/disconnects
        # and long-running processes can cause stale file handles,
        # resulting in 'file not found' errors on files that do exist.
        # Re-mounting the network drive is the only remediation
        # which I've been able to find that works, but the particular
        # mount options can vary wildly. So, it seems best that clusters
        # should use pre-configured scripts to refresh networked storage.
        remount_script = ''
        if 'remount_script' in chip.status:
            # Note: 'sc' is not typically run as root, so hosts in the
            # slurm cluster will need permission to run this command.
            # The 'visudo' command can be used to set such permissions.
            remount_script = f"sudo {chip.status['remount_script']}"

        # The deferred execution command needs to:
        # * copy encrypted data/key and unencrypted IV into local storage.
        # * store the provided key in local storage.
        # * call 'sc' with the provided key, wait for the job to finish.
        # * copy encrypted data for the completed step into shared storage.
        # * delete all unencrypted data.
        run_cmd  = f'{schedule_cmd} bash -c "'
        run_cmd += f"mkdir -p {tmp_build_dir} ; "
        run_cmd += f"{remount_script} ; "
        run_cmd += f"rsync -a {ctrl_node_dir}/* {tmp_job_dir}/ ; "
        run_cmd += f"touch {keypath} ; chmod 600 {keypath} ; "
        run_cmd += f"echo -ne '{keystr}' > {keypath} ; "
        run_cmd += f"chmod 400 {keypath} ; "
        run_cmd += f"sc-crypt -mode decrypt_config "\
                       f"-target {tmp_build_dir}/configs/{step}{index}.crypt "\
                       f"-key_file {keypath} ; "
        run_cmd += f"sc-crypt -mode decrypt -target {tmp_build_dir} "\
                       f"-key_file {keypath} ; "
        run_cmd += f"sc -cfg {tmp_build_dir}/configs/{step}{index}.json "\
                       f"-arg_step {step} -arg_index {index} "\
                       f"-dir {tmp_job_dir} -jobscheduler '' ; "
        run_cmd += f"retcode=\\$? ; "
        run_cmd += f"sc-crypt -mode encrypt -target {tmp_build_dir} "\
                       f"-key_file {keypath} ; "
        run_cmd += f"{remount_script} ; "
        run_cmd += f"rsync -a {tmp_build_dir}/{step}* "\
                       f"{cur_build_dir}/ ; "
        run_cmd += f"rm -rf {tmp_job_dir} ; "
        run_cmd += f"exit \\$retcode"
        run_cmd += '"'
    else:
        # Job data is not encrypted, so it can be run in shared storage.
        # Write out the current schema for the compute node to pick up.
        job_dir = "/".join([chip.get('dir'),
                            chip.get('design'),
                            chip.get('jobname')])
        cfg_dir = f'{job_dir}/configs'
        cfg_file = f'{cfg_dir}/{step}{index}.json'
        if not os.path.isdir(cfg_dir):
            os.mkdir(cfg_dir)
        chip.write_manifest(cfg_file)

        # Create a command to defer execution to a compute node.
        script_path = f'{cfg_dir}/{step}{index}.sh'
        with open(script_path, 'w') as sf:
            sf.write('#!/bin/bash\n')
            sf.write(f'sc -cfg {cfg_file} -dir {chip.get("dir")} '\
                     f'-arg_step {step} -arg_index {index} '\
                     f"-jobscheduler ''")
        run_cmd = f'{schedule_cmd} {script_path}'

    # Run the 'srun' command, and track its output.
    step_result = subprocess.Popen(run_cmd,
                                   shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)

    # TODO: output should be fed to log, and stdout if quiet = False

    # Wait for the subprocess call to complete. It should already be done,
    # as it has closed its output stream. But if we don't call '.wait()',
    # the '.returncode' value will not be set correctly.
    step_result.wait()
    result_msg = step_result.stdout.read().decode()
    sbatch_id = result_msg.split(' ')[-1]
    retcode = 0
    while True:
        time.sleep(3.0)

        # If a maximum disk space was defined, ensure that it is respected.
        if 'max_fs_bytes' in chip.status:
            du_cmd = subprocess.run(['du', '-sb', chip.get('dir')],
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
        jobcheck = subprocess.run(f'scontrol show job {sbatch_id}',
                                  shell=True,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)
        jobout = jobcheck.stdout.decode()
        if ('RUNNING' in jobout) or ('PENDING' in jobout):
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

    # Clear active bit after the 'srun' command, and set 'error' accordingly.
    error[step + str(index)] = retcode
    active[step + str(index)] = 0
