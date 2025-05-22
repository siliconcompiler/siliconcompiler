import os
import shlex
import subprocess
import stat
import uuid
import json
import shutil
from siliconcompiler import utils, SiliconCompilerError
from siliconcompiler.package import get_cache_path
from siliconcompiler.flowgraph import RuntimeFlowgraph

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
def get_configuration_directory(chip):
    '''
    Helper function to get the configuration directory for the scheduler
    '''

    return f'{chip.getworkdir()}/configs'


def init(chip):
    if os.path.exists(chip._getcollectdir()):
        # nothing to do
        return

    collect = False
    flow = chip.get('option', 'flow')
    entry_nodes = chip.schema.get("flowgraph", flow, field="schema").get_entry_nodes()

    runtime = RuntimeFlowgraph(
        chip.schema.get("flowgraph", flow, field='schema'),
        from_steps=chip.get('option', 'from'),
        to_steps=chip.get('option', 'to'),
        prune_nodes=chip.get('option', 'prune'))

    for (step, index) in runtime.get_nodes():
        if (step, index) in entry_nodes:
            collect = True

    if collect:
        chip.collect()


###########################################################################
def _defernode(chip, step, index, replay):
    '''
    Helper method to run an individual step on a slurm cluster.

    Blocks until the compute node
    finishes processing this step, and it sets the active/error bits.
    '''

    # Determine which HPC job scheduler being used.
    scheduler_type = chip.get('option', 'scheduler', 'name', step=step, index=index)

    if scheduler_type != 'slurm':
        raise ValueError(f'{scheduler_type} is not a supported scheduler')

    if not check_slurm():
        raise SiliconCompilerError('slurm is not available or installed on this machine', chip=chip)

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
    cfg_dir = get_configuration_directory(chip)
    cfg_file = f'{cfg_dir}/{step}{index}.json'
    log_file = f'{cfg_dir}/{step}{index}.log'
    script_file = f'{cfg_dir}/{step}{index}.sh'
    os.makedirs(cfg_dir, exist_ok=True)

    chip.set('option', 'scheduler', 'name', None, step=step, index=index)
    chip.write_manifest(cfg_file)

    # Allow user-defined compute node execution script if it already exists on the filesystem.
    # Otherwise, create a minimal script to run the task using the SiliconCompiler CLI.
    if not os.path.isfile(script_file):
        with open(script_file, 'w') as sf:
            sf.write(utils.get_file_template('slurm/run.sh').render(
                cfg_file=shlex.quote(cfg_file),
                build_dir=shlex.quote(chip.get("option", "builddir")),
                step=shlex.quote(step),
                index=shlex.quote(index),
                cachedir=shlex.quote(get_cache_path(chip))
            ))

    # This is Python for: `chmod +x [script_path]`
    os.chmod(script_file,
             os.stat(script_file).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    schedule_cmd = ['srun',
                    '--exclusive',
                    '--partition', partition,
                    '--chdir', chip.cwd,
                    '--job-name', job_name,
                    '--output', log_file]

    # Only delay the starting time if the 'defer' Schema option is specified.
    defer_time = chip.get('option', 'scheduler', 'defer', step=step, index=index)
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


def _get_slurm_partition():
    partitions = subprocess.run(['sinfo', '--json'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

    if partitions.returncode != 0:
        raise RuntimeError('Unable to determine partitions in slurm')

    sinfo = json.loads(partitions.stdout.decode())

    # Return the first listed partition
    return sinfo['nodes'][0]['partitions'][0]


def check_slurm():
    return shutil.which('sinfo') is not None
