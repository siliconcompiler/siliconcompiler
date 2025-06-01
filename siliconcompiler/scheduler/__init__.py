import logging
import os
import re
import shutil
import sys
from logging.handlers import QueueHandler
from siliconcompiler import sc_open
from siliconcompiler import utils
from siliconcompiler.remote import Client
from siliconcompiler import Schema
from siliconcompiler.schema import JournalingSchema
from siliconcompiler.record import RecordTime, RecordTool
from siliconcompiler import NodeStatus, SiliconCompilerError
from siliconcompiler.tools._common import input_file_node_name
import lambdapdk
from siliconcompiler.tools._common import get_tool_task, record_metric
from siliconcompiler.scheduler import send_messages
from siliconcompiler.flowgraph import RuntimeFlowgraph
from siliconcompiler.scheduler.taskscheduler import TaskScheduler


# Max lines to print from failed node log
_failed_log_lines = 20


###############################################################################
class SiliconCompilerTimeout(Exception):
    ''' Minimal Exception wrapper used to raise sc timeout errors.
    '''
    def __init__(self, message):
        super(Exception, self).__init__(message)


def run(chip):
    '''
    See :meth:`~siliconcompiler.core.Chip.run` for detailed documentation.
    '''

    _check_display(chip)

    # Check required settings before attempting run()
    for key in (['option', 'flow'], ):
        if chip.get(*key) is None:
            raise SiliconCompilerError(
                f"{key} must be set before calling run()",
                chip=chip)

    org_jobname = chip.get('option', 'jobname')
    _increment_job_name(chip)

    # Re-init logger to include run info after setting up flowgraph.
    chip._init_logger(in_run=True)
    if chip._dash and not chip._dash.is_running():
        chip._dash.open_dashboard()

    # Check if flowgraph is complete and valid
    flow = chip.get('option', 'flow')
    if not chip.schema.get("flowgraph", flow, field="schema").validate(logger=chip.logger):
        raise SiliconCompilerError(
            f"{flow} flowgraph contains errors and cannot be run.",
            chip=chip)
    if not RuntimeFlowgraph.validate(
            chip.schema.get("flowgraph", flow, field="schema"),
            from_steps=chip.get('option', 'from'),
            to_steps=chip.get('option', 'to'),
            prune_nodes=chip.get('option', 'prune'),
            logger=chip.logger):
        raise SiliconCompilerError(
            f"{flow} flowgraph contains errors and cannot be run.",
            chip=chip)

    copy_old_run_dir(chip, org_jobname)
    clean_build_dir(chip)

    runtime = RuntimeFlowgraph(
        chip.schema.get("flowgraph", flow, field='schema'),
        from_steps=chip.get('option', 'from'),
        to_steps=chip.get('option', 'to'),
        prune_nodes=chip.get('option', 'prune'))

    _reset_flow_nodes(chip, flow, runtime.get_nodes())
    chip.schema.get("record", field='schema').record_python_packages()

    if chip.get('option', 'remote'):
        client = Client(chip)
        client.run()
    else:
        _local_process(chip, flow)

    # Merge cfgs from last executed tasks, and write out a final manifest.
    _finalize_run(chip)


###########################################################################
def _finalize_run(chip):
    '''
    Helper function to finalize a job run after it completes:
    * Clear any -arg_step/-arg_index values in case only one node was run.
    * Store this run in the Schema's 'history' field.
    * Write out a final JSON manifest containing the full results and history.
    '''

    # Clear scratchpad args since these are checked on run() entry
    chip.set('arg', 'step', None, clobber=True)
    chip.set('arg', 'index', None, clobber=True)

    # Store run in history
    chip.schema.record_history()

    # Storing manifest in job root directory
    filepath = os.path.join(chip.getworkdir(), f"{chip.design}.pkg.json")
    chip.write_manifest(filepath)

    send_messages.send(chip, 'summary', None, None)


def _increment_job_name(chip):
    '''
    Auto-update jobname if ['option', 'jobincr'] is True
    Do this before initializing logger so that it picks up correct jobname
    '''
    if not chip.get('option', 'clean'):
        return
    if chip.get('option', 'jobincr'):
        workdir = chip.getworkdir()
        if os.path.isdir(workdir):
            # Strip off digits following jobname, if any
            stem = chip.get('option', 'jobname').rstrip('0123456789')

            designdir = os.path.dirname(workdir)
            jobid = 0
            for job in os.listdir(designdir):
                m = re.match(stem + r'(\d+)', job)
                if m:
                    jobid = max(jobid, int(m.group(1)))
            chip.set('option', 'jobname', f'{stem}{jobid + 1}')


###########################################################################
def _check_display(chip):
    '''
    Automatically disable display for Linux systems without desktop environment
    '''
    if not chip.get('option', 'nodisplay') and sys.platform == 'linux' \
            and 'DISPLAY' not in os.environ and 'WAYLAND_DISPLAY' not in os.environ:
        chip.logger.warning('Environment variable $DISPLAY or $WAYLAND_DISPLAY not set')
        chip.logger.warning("Setting ['option', 'nodisplay'] to True")
        chip.set('option', 'nodisplay', True)


def _local_process(chip, flow):
    from_nodes = []
    extra_setup_nodes = {}

    chip.schema = JournalingSchema(chip.schema)
    chip.schema.start_journal()

    if chip.get('option', 'clean') or not chip.get('option', 'from'):
        load_nodes = list(chip.schema.get("flowgraph", flow, field="schema").get_nodes())
    else:
        for step in chip.get('option', 'from'):
            from_nodes.extend(
                [(step, index) for index in chip.getkeys('flowgraph', flow, step)])

        runtime = RuntimeFlowgraph(
            chip.schema.get("flowgraph", flow, field="schema"),
            to_steps=chip.get('option', 'from'),
            prune_nodes=chip.get('option', 'prune'))
        load_nodes = list(runtime.get_nodes())

    for node_level in chip.schema.get("flowgraph", flow, field="schema").get_execution_order():
        for step, index in node_level:
            if (step, index) not in load_nodes:
                continue
            if (step, index) in from_nodes:
                continue

            manifest = os.path.join(chip.getworkdir(step=step, index=index),
                                    'outputs',
                                    f'{chip.design}.pkg.json')
            if os.path.exists(manifest):
                # ensure we setup these nodes again
                try:
                    journal = JournalingSchema(Schema())
                    journal.read_manifest(manifest)
                    extra_setup_nodes[(step, index)] = journal
                except Exception:
                    pass

    runtimeflow = RuntimeFlowgraph(
        chip.schema.get("flowgraph", flow, field="schema"),
        from_steps=chip.get('option', 'from'),
        to_steps=chip.get('option', 'to'),
        prune_nodes=chip.get('option', 'prune'))

    # Setup tools for all nodes to run.
    nodes = list(runtimeflow.get_nodes())
    all_setup_nodes = nodes + load_nodes + list(extra_setup_nodes.keys())
    for layer_nodes in chip.schema.get("flowgraph", flow, field="schema").get_execution_order():
        for step, index in layer_nodes:
            if (step, index) in all_setup_nodes:
                node_kept = _setup_node(chip, step, index)
                if not node_kept and (step, index) in extra_setup_nodes:
                    del extra_setup_nodes[(step, index)]
                if (step, index) in extra_setup_nodes:
                    schema = extra_setup_nodes[(step, index)]
                    node_status = None
                    try:
                        node_status = schema.get('record', 'status', step=step, index=index)
                    except:  # noqa E722
                        pass
                    if node_status:
                        chip.schema.get("record", field='schema').set('status', node_status,
                                                                      step=step, index=index)

    def mark_pending(step, index):
        chip.schema.get("record", field='schema').set('status', NodeStatus.PENDING,
                                                      step=step, index=index)
        for next_step, next_index in runtimeflow.get_nodes_starting_at(step, index):
            if chip.get('record', 'status', step=next_step, index=next_index) == \
                    NodeStatus.SKIPPED:
                continue

            # Mark following steps as pending
            chip.schema.get("record", field='schema').set('status', NodeStatus.PENDING,
                                                          step=next_step, index=next_index)

    # Check if nodes have been modified from previous data
    for layer_nodes in chip.schema.get("flowgraph", flow, field="schema").get_execution_order():
        for step, index in layer_nodes:
            # Only look at successful nodes
            if chip.get('record', 'status', step=step, index=index) not in \
                    (NodeStatus.SUCCESS, NodeStatus.SKIPPED):
                continue

            if (step, index) in runtimeflow.get_nodes() and \
                    not check_node_inputs(chip, step, index):
                # change failing nodes to pending
                mark_pending(step, index)
            elif (step, index) in extra_setup_nodes:
                # import old information
                chip.schema.import_journal(schema=extra_setup_nodes[(step, index)])

    # Ensure pending nodes cause following nodes to be run
    for step, index in nodes:
        if chip.get('record', 'status', step=step, index=index) in \
                (NodeStatus.PENDING, NodeStatus.ERROR):
            mark_pending(step, index)

    # Clean nodes marked pending
    for step, index in nodes:
        if chip.get('record', 'status', step=step, index=index) == NodeStatus.PENDING:
            clean_node_dir(chip, step, index)

    chip.write_manifest(os.path.join(chip.getworkdir(), f"{chip.get('design')}.pkg.json"))
    chip.schema.stop_journal()
    chip.schema = chip.schema.get_base_schema()

    # Check validity of setup
    chip.logger.info("Checking manifest before running.")
    check_ok = chip.check_manifest()

    # Check if there were errors before proceeding with run
    if not check_ok:
        raise SiliconCompilerError('Manifest check failed. See previous errors.', chip=chip)

    if chip._error:
        raise SiliconCompilerError(
            'Implementation errors encountered. See previous errors.',
            chip=chip)

    task_scheduler = TaskScheduler(chip)
    task_scheduler.run()

    _check_nodes_status(chip, flow)


###########################################################################
def _setup_node(chip, step, index, flow=None):
    preset_step = chip.get('arg', 'step')
    preset_index = chip.get('arg', 'index')
    preset_flow = chip.get('option', 'flow')

    if flow:
        chip.set('option', 'flow', flow)

    chip.set('arg', 'step', step)
    chip.set('arg', 'index', index)
    tool, task = get_tool_task(chip, step, index, flow=flow)

    task_class = chip.get("tool", tool, field="schema")
    task_class.set_runtime(chip)

    # Run node setup.
    chip.logger.info(f'Setting up node {step}{index} with {tool}/{task}')
    setup_ret = None
    try:
        setup_ret = task_class.setup()
    except Exception as e:
        chip.logger.error(f'Failed to run setup() for {tool}/{task}')
        raise e

    task_class.set_runtime(None)

    # Need to restore step/index, otherwise we will skip setting up other indices.
    chip.set('option', 'flow', preset_flow)
    chip.set('arg', 'step', preset_step)
    chip.set('arg', 'index', preset_index)

    if setup_ret is not None:
        chip.logger.warning(f'Removing {step}{index} due to {setup_ret}')
        chip.schema.get("record", field='schema').set('status', NodeStatus.SKIPPED,
                                                      step=step, index=index)

        return False

    return True


###########################################################################
def _runtask(chip, flow, step, index, exec_func, pipe=None, queue=None, replay=False):
    '''
    Private per node run method called by run().

    The method takes in a step string and index string to indicate what
    to run.

    Note that since _runtask occurs in its own process with a separate
    address space, any changes made to the `self` object will not
    be reflected in the parent. We rely on reading/writing the chip manifest
    to the filesystem to communicate updates between processes.
    '''

    chip._init_codecs()

    chip._init_logger(step, index, in_run=True)
    if queue:
        chip.logger.removeHandler(chip.logger._console)
        chip.logger._console = QueueHandler(queue)
        chip.logger.addHandler(chip.logger._console)
        chip._init_logger_formats()

    chip.set('arg', 'step', step, clobber=True)
    chip.set('arg', 'index', index, clobber=True)

    chip.schema = JournalingSchema(chip.schema)
    chip.schema.start_journal()

    # Make record of sc version and machine
    chip.schema.get("record", field='schema').record_version(step, index)
    # Record user information if enabled
    if chip.get('option', 'track', step=step, index=index):
        chip.schema.get("record", field='schema').record_userinformation(step, index)

    # Start wall timer
    chip.schema.get("record", field='schema').record_time(step, index, RecordTime.START)

    workdir = _setup_workdir(chip, step, index, replay)
    cwd = os.getcwd()
    os.chdir(workdir)

    chip._add_file_logger(os.path.join(workdir, f'sc_{step}{index}.log'))

    try:
        _setupnode(chip, flow, step, index, replay)

        exec_func(chip, step, index, replay)
    except Exception as e:
        utils.print_traceback(chip.logger, e)
        _haltstep(chip, chip.get('option', 'flow'), step, index)

    # return to original directory
    os.chdir(cwd)
    chip.schema.stop_journal()
    chip.schema = chip.schema.get_base_schema()

    if pipe:
        pipe.send(chip._packages)


###########################################################################
def _haltstep(chip, flow, step, index, log=True):
    chip.schema.get("record", field='schema').set('status', NodeStatus.ERROR,
                                                  step=step, index=index)
    chip.write_manifest(os.path.join("outputs", f"{chip.get('design')}.pkg.json"))

    if log:
        chip.logger.error(f"Halting step '{step}' index '{index}' due to errors.")
        send_messages.send(chip, "fail", step, index)
    sys.exit(1)


def _setupnode(chip, flow, step, index, replay):
    _hash_files(chip, step, index, setup=True)

    # Select the inputs to this node
    _select_inputs(chip, step, index)

    # Write manifest prior to step running into inputs
    chip.write_manifest(f'inputs/{chip.get("design")}.pkg.json')

    # Forward data
    _copy_previous_steps_output_data(chip, step, index, replay)

    # Check manifest
    if not _check_manifest_dynamic(chip, step, index):
        chip.logger.error("Fatal error in check_manifest()! See previous errors.")
        _haltstep(chip, flow, step, index)


###########################################################################
def _setup_workdir(chip, step, index, replay):
    workdir = chip.getworkdir(step=step, index=index)

    if os.path.isdir(workdir) and not replay:
        shutil.rmtree(workdir)
    os.makedirs(workdir, exist_ok=True)
    os.makedirs(os.path.join(workdir, 'inputs'), exist_ok=True)
    os.makedirs(os.path.join(workdir, 'outputs'), exist_ok=True)
    os.makedirs(os.path.join(workdir, 'reports'), exist_ok=True)
    return workdir


def _select_inputs(chip, step, index, trial=False):

    flow = chip.get('option', 'flow')
    tool, _ = get_tool_task(chip, step, index, flow)

    task_class = chip.get("tool", tool, field="schema")
    task_class.set_runtime(chip, step=step, index=index)

    log_level = chip.logger.level
    if trial:
        chip.logger.setLevel(logging.CRITICAL)

    sel_inputs = task_class.select_input_nodes()

    if trial:
        chip.logger.setLevel(log_level)

    if (step, index) not in chip.schema.get("flowgraph", flow, field="schema").get_entry_nodes() \
            and not sel_inputs:
        chip.logger.error(f'No inputs selected after running {tool}')
        _haltstep(chip, flow, step, index)

    if not trial:
        chip.schema.get("record", field='schema').set('inputnode', sel_inputs,
                                                      step=step, index=index)

    return sel_inputs


def copy_output_file(chip, outfile, folder='inputs'):
    design = chip.get('design')

    if outfile.is_file() or outfile.is_symlink():
        if outfile.name == f'{design}.pkg.json':
            return
        utils.link_symlink_copy(outfile.path, f'{folder}/{outfile.name}')
    elif outfile.is_dir():
        shutil.copytree(outfile.path,
                        f'{folder}/{outfile.name}',
                        dirs_exist_ok=True,
                        copy_function=utils.link_symlink_copy)


def forward_output_files(chip, step, index):
    for in_step, in_index in chip.get('record', 'inputnode', step=step, index=index):
        in_workdir = chip.getworkdir(step=in_step, index=in_index)
        for outfile in os.scandir(f"{in_workdir}/outputs"):
            copy_output_file(chip, outfile, folder='outputs')


def _copy_previous_steps_output_data(chip, step, index, replay):
    '''
    Copy (link) output data from previous steps
    '''

    flow = chip.get('option', 'flow')

    flow_schema = chip.schema.get("flowgraph", flow, field="schema")
    runtime = RuntimeFlowgraph(
        flow_schema,
        from_steps=set([step for step, _ in flow_schema.get_entry_nodes()]),
        prune_nodes=chip.get('option', 'prune'))

    if not runtime.get_node_inputs(step, index, record=chip.schema.get("record", field="schema")):
        all_inputs = []
    elif not chip.get('record', 'inputnode', step=step, index=index):
        all_inputs = runtime.get_node_inputs(step, index,
                                             record=chip.schema.get("record", field="schema"))
    else:
        all_inputs = chip.get('record', 'inputnode', step=step, index=index)

    strict = chip.get('option', 'strict')
    tool, task = get_tool_task(chip, step, index)
    in_files = chip.get('tool', tool, 'task', task, 'input', step=step, index=index)
    for in_step, in_index in all_inputs:
        if chip.get('record', 'status', step=in_step, index=in_index) == NodeStatus.ERROR:
            chip.logger.error(f'Halting step due to previous error in {in_step}{in_index}')
            _haltstep(chip, flow, step, index)

        # Skip copying pkg.json files here, since we write the current chip
        # configuration into inputs/{design}.pkg.json earlier in _runstep.
        if not replay:
            in_workdir = chip.getworkdir(step=in_step, index=in_index)
            output_dir = os.path.join(in_workdir, "outputs")

            if not os.path.isdir(output_dir):
                chip.logger.error(
                    f'Unable to locate outputs directory for {in_step}{in_index}: {output_dir}')
                _haltstep(chip, flow, step, index)

            for outfile in os.scandir(output_dir):
                new_name = input_file_node_name(outfile.name, in_step, in_index)
                if strict:
                    if outfile.name not in in_files and new_name not in in_files:
                        continue

                copy_output_file(chip, outfile)

                if new_name in in_files:
                    # perform rename
                    os.rename(f'inputs/{outfile.name}', f'inputs/{new_name}')


############################################################################
# Chip helper Functions
############################################################################
def _check_logfile(chip, step, index, quiet=False, run_func=None):
    '''
    Check log file (must be after post-process)
    '''
    if run_func is None:
        tool, task = get_tool_task(chip, step, index)

        log_file = os.path.join(chip.getworkdir(step=step, index=index), f'{step}.log')
        matches = check_logfile(chip, step=step, index=index,
                                display=not quiet,
                                logfile=log_file)
        if 'errors' in matches:
            errors = chip.get('metric', 'errors', step=step, index=index)
            if errors is None:
                errors = 0
            errors += matches['errors']

            sources = [f'{step}.log']
            if chip.valid('tool', tool, 'task', task, 'regex', 'errors'):
                if chip.get('tool', tool, 'task', task, 'regex', 'errors',
                            step=step, index=index):
                    sources.append(f'{step}.errors')

            record_metric(chip, step, index, 'errors', errors, sources)
        if 'warnings' in matches:
            warnings = chip.get('metric', 'warnings', step=step, index=index)
            if warnings is None:
                warnings = 0
            warnings += matches['warnings']

            sources = [f'{step}.log']
            if chip.valid('tool', tool, 'task', task, 'regex', 'warnings'):
                if chip.get('tool', tool, 'task', task, 'regex', 'warnings',
                            step=step, index=index):
                    sources.append(f'{step}.warnings')

            record_metric(chip, step, index, 'warnings', warnings, sources)


def _executenode(chip, step, index, replay):
    workdir = chip.getworkdir(step=step, index=index)
    flow = chip.get('option', 'flow')
    tool, task = get_tool_task(chip, step, index, flow)

    task_class = chip.get("tool", tool, field="schema")
    task_class.set_runtime(chip)

    chip.logger.info(f'Running in {workdir}')

    try:
        task_class.pre_process()
    except Exception as e:
        chip.logger.error(f"Pre-processing failed for '{tool}/{task}'.")
        utils.print_traceback(chip.logger, e)
        raise e

    if chip.get('record', 'status', step=step, index=index) == NodeStatus.SKIPPED:
        # copy inputs to outputs and skip execution
        forward_output_files(chip, step, index)

        send_messages.send(chip, "skipped", step, index)
    else:
        org_env = os.environ.copy()
        os.environ.update(task_class.get_runtime_environmental_variables())

        toolpath = task_class.get_exe()
        version = task_class.get_exe_version()

        if not chip.get('option', 'novercheck', step=step, index=index):
            if not task_class.check_exe_version(version):
                _haltstep(chip, flow, step, index)

        if version:
            chip.schema.get("record", field='schema').record_tool(
                step, index, version, RecordTool.VERSION)

        if toolpath:
            chip.schema.get("record", field='schema').record_tool(
                step, index, toolpath, RecordTool.PATH)

        send_messages.send(chip, "begin", step, index)

        try:
            if not replay:
                task_class.generate_replay_script(
                    os.path.join(workdir, "replay.sh"),
                    workdir)
            ret_code = task_class.run_task(
                workdir,
                chip.get('option', 'quiet', step=step, index=index),
                chip.get('option', 'loglevel', step=step, index=index),
                chip.get('option', 'breakpoint', step=step, index=index),
                chip.get('option', 'nice', step=step, index=index),
                chip.get('option', 'timeout', step=step, index=index))
        except Exception as e:
            raise e

        os.environ.clear()
        os.environ.update(org_env)

        if ret_code != 0:
            msg = f'Command failed with code {ret_code}.'
            logfile = f"{step}.log"
            if os.path.exists(logfile):
                if chip.get('option', 'quiet', step=step, index=index):
                    # Print last N lines of log when in quiet mode
                    with sc_open(logfile) as logfd:
                        loglines = logfd.read().splitlines()
                        for logline in loglines[-_failed_log_lines:]:
                            chip.logger.error(logline)
                    # No log file for pure-Python tools.
                msg += f' See log file {os.path.abspath(logfile)}'
            chip.logger.warning(msg)
            chip._error = True

        try:
            task_class.post_process()
        except Exception as e:
            chip.logger.error(f"Post-processing failed for '{tool}/{task}'.")
            utils.print_traceback(chip.logger, e)
            chip._error = True

    _finalizenode(chip, step, index, replay)

    send_messages.send(chip, "end", step, index)


def _hash_files(chip, step, index, setup=False):
    if chip._error:
        return

    flow = chip.get('option', 'flow')
    tool, task = get_tool_task(chip, step, index, flow)
    if chip.get('option', 'hash'):
        if not setup:
            # hash all outputs
            chip.hash_files('tool', tool, 'task', task, 'output',
                            step=step, index=index, check=False, verbose=False)
        else:
            for task_key in ('refdir', 'prescript', 'postscript', 'script'):
                chip.hash_files('tool', tool, 'task', task, task_key,
                                step=step, index=index, check=False,
                                allow_cache=True, verbose=False)

        # hash all requirements
        for item in set(chip.get('tool', tool, 'task', task, 'require', step=step, index=index)):
            args = item.split(',')
            sc_type = chip.get(*args, field='type')
            if 'file' in sc_type or 'dir' in sc_type:
                if chip.get(*args, field='pernode').is_never():
                    if not setup:
                        if chip.get(*args, field='filehash'):
                            continue
                    chip.hash_files(*args, check=False, allow_cache=True, verbose=False)
                else:
                    if not setup:
                        if chip.get(*args, field='filehash', step=step, index=index):
                            continue
                    chip.hash_files(*args, step=step, index=index,
                                    check=False, allow_cache=True, verbose=False)


def _finalizenode(chip, step, index, replay):
    if chip.schema.is_journaling() and any(
            [record["type"] == "get" for record in chip.schema.get_journal()]):
        assert_required_accesses(chip, step, index)

    flow = chip.get('option', 'flow')
    tool, task = get_tool_task(chip, step, index, flow)
    quiet = (
        chip.get('option', 'quiet', step=step, index=index) and not
        chip.get('option', 'breakpoint', step=step, index=index)
    )

    is_skipped = chip.get('record', 'status', step=step, index=index) == NodeStatus.SKIPPED

    if not is_skipped:
        _check_logfile(chip, step, index, quiet, None)

    # Report metrics
    for metric in ['errors', 'warnings']:
        val = chip.get('metric', metric, step=step, index=index)
        if val is not None:
            chip.logger.info(f'Number of {metric}: {val}')

    _hash_files(chip, step, index)

    # Capture wall runtime and cpu cores
    end_time = chip.schema.get("record", field='schema').record_time(step, index, RecordTime.END)

    walltime = end_time - chip.schema.get("record", field='schema').get_recorded_time(
        step, index, RecordTime.START)
    record_metric(chip, step, index, 'tasktime', walltime,
                  source=None, source_unit='s')

    chip.schema.get("metric", field='schema').record_totaltime(
        step, index,
        chip.schema.get("flowgraph", flow, field='schema'),
        chip.schema.get("record", field='schema'))
    chip.logger.info(f"Finished task in {round(walltime, 2)}s")

    # Save a successful manifest
    if not is_skipped:
        chip.schema.get("record", field='schema').set('status', NodeStatus.SUCCESS,
                                                      step=step, index=index)

    chip.write_manifest(os.path.join("outputs", f"{chip.get('design')}.pkg.json"))

    if chip._error and not replay:
        _make_testcase(chip, step, index)

    # Stop if there are errors
    errors = chip.get('metric', 'errors', step=step, index=index)
    if errors and not chip.get('option', 'continue', step=step, index=index):
        # TODO: should we warn if errors is not set?
        chip.logger.error(f'{tool} reported {errors} errors during {step}{index}')
        _haltstep(chip, flow, step, index)

    if chip._error:
        _haltstep(chip, flow, step, index)

    if chip.get('option', 'strict'):
        assert_output_files(chip, step, index)


def _make_testcase(chip, step, index):
    # Import here to avoid circular import
    from siliconcompiler.utils.issue import generate_testcase

    generate_testcase(
        chip,
        step,
        index,
        archive_directory=chip.getworkdir(),
        include_pdks=False,
        include_specific_pdks=lambdapdk.get_pdks(),
        include_libraries=False,
        include_specific_libraries=lambdapdk.get_libs(),
        hash_files=chip.get('option', 'hash'),
        verbose_collect=False)


def assert_output_files(chip, step, index):
    flow = chip.get('option', 'flow')
    tool, task = get_tool_task(chip, step, index, flow)

    if tool == 'builtin':
        return

    outputs = os.listdir(f'{chip.getworkdir(step=step, index=index)}/outputs')
    outputs.remove(f'{chip.design}.pkg.json')

    output_files = chip.get('tool', tool, 'task', task, 'output',
                            step=step, index=index)

    if set(outputs) != set(output_files):
        raise SiliconCompilerError(
            f'Output files set {output_files} for {step}{index} does not match generated '
            f'outputs: {outputs}',
            chip=chip)


def assert_required_accesses(chip, step, index):
    flow = chip.get('option', 'flow')
    jobname = chip.get('option', 'jobname')
    tool, task = get_tool_task(chip, step, index, flow)

    if tool == 'builtin':
        return

    gets = set([tuple(record["key"]) for record in chip.schema.get_journal()
                if record["type"] == "get"])
    logfile = os.path.join(
        chip.getworkdir(jobname=jobname, step=step, index=index),
        f'{step}.log')

    with sc_open(logfile) as f:
        for line in f:
            if line.startswith(Schema._RECORD_ACCESS_IDENTIFIER):
                key = line[len(Schema._RECORD_ACCESS_IDENTIFIER):].strip().split(',')
                if chip.valid(*key, check_complete=True):
                    gets.add(tuple(key))

    def get_value(*key):
        if chip.get(*key, field='pernode').is_never():
            return chip.get(*key)
        else:
            return chip.get(*key, step=step, index=index)

    getkeys = set()
    # Remove keys with empty values
    for key in set(sorted(gets)):
        if get_value(*key):
            getkeys.add(key)

    # Remove keys that dont matter
    exempt = [
        ('design',),
        ('arg', 'step'), ('arg', 'index'),
        ('option', 'jobname'), ('option', 'flow'), ('option', 'strict'), ('option', 'builddir'),
        ('option', 'quiet'),
        ('tool', tool, 'exe'),
        ('tool', tool, 'task', task, 'require'),
        ('tool', tool, 'task', task, 'threads'),
        ('flowgraph', flow, step, index, 'tool'), ('flowgraph', flow, step, index, 'task'),
        ('flowgraph', flow, step, index, 'taskmodule')]
    for key in chip.getkeys('metric'):
        exempt.append(('metric', key))
    for key in chip.getkeys('tool', tool, 'task', task, 'report'):
        exempt.append(('tool', tool, 'task', task, 'report', key))

    required = set(
        [tuple(key.split(',')) for key in chip.get('tool', tool, 'task', task, 'require',
                                                   step=step, index=index)])

    for key in set(exempt):
        if key in getkeys:
            getkeys.remove(key)
        if key in required:
            required.remove(key)

    excess_require = required.difference(getkeys)
    if True:
        for key in sorted(excess_require):
            chip.logger.error(f"{step}{index} does not require requirement: {','.join(key)}")
    missing_require = getkeys.difference(required)
    for key in sorted(missing_require):
        chip.logger.error(f"{step}{index} has an unexpressed requirement: "
                          f"{','.join(key)} = {get_value(*key)}")

    if missing_require:
        raise SiliconCompilerError(
            f'Requirements for {step}{index} does not match access list: '
            f'{", ".join([",".join(key) for key in sorted(missing_require)])}',
            chip=chip)


def _reset_flow_nodes(chip, flow, nodes_to_execute):
    # Reset flowgraph/records/metrics by probing build directory. We need
    # to set values to None for steps we may re-run so that merging
    # manifests from _runtask() actually updates values.

    def clear_node(step, index):
        # Reset metrics and records
        chip.schema.get("metric", field='schema').clear(step, index)
        for metric in chip.getkeys('metric'):
            _clear_metric(chip, step, index, metric)

        chip.schema.get("record", field='schema').clear(
            step, index, keep=['remoteid', 'status', 'pythonpackage'])

    # Mark all nodes as pending
    for step, index in chip.schema.get("flowgraph", flow, field="schema").get_nodes():
        chip.schema.get("record", field='schema').set('status', NodeStatus.PENDING,
                                                      step=step, index=index)

    should_resume = not chip.get('option', 'clean')
    for step, index in chip.schema.get("flowgraph", flow, field="schema").get_nodes():
        stepdir = chip.getworkdir(step=step, index=index)
        cfg = f"{stepdir}/outputs/{chip.get('design')}.pkg.json"

        if not os.path.isdir(stepdir) or (
                (step, index) in nodes_to_execute and not should_resume):
            # If stepdir doesn't exist, we need to re-run this task. If
            # we're not running with -resume, we also re-run anything
            # in the nodes to execute.
            clear_node(step, index)
        elif os.path.isfile(cfg):
            try:
                old_status = Schema(manifest=cfg).get('record', 'status', step=step, index=index)
                if old_status:
                    chip.schema.get("record", field='schema').set('status', old_status,
                                                                  step=step, index=index)
            except Exception:
                # unable to load so leave it default
                pass
        else:
            chip.schema.get("record", field='schema').set('status', NodeStatus.ERROR,
                                                          step=step, index=index)

    for step in chip.getkeys('flowgraph', flow):
        all_indices_failed = True
        for index in chip.getkeys('flowgraph', flow, step):
            if chip.get('record', 'status', step=step, index=index) == NodeStatus.SUCCESS:
                all_indices_failed = False

        if should_resume and all_indices_failed:
            # When running with -resume, we re-run any step in flowgraph that
            # had all indices fail.
            for index in chip.getkeys('flowgraph', flow, step):
                if (step, index) in nodes_to_execute:
                    clear_node(step, index)


def _check_nodes_status(chip, flow):
    flowgraph = chip.schema.get("flowgraph", flow, field="schema")
    runtime = RuntimeFlowgraph(
        flowgraph,
        from_steps=chip.get('option', 'from'),
        to_steps=chip.get('option', 'to'),
        prune_nodes=chip.get('option', 'prune'))
    runtime_no_prune = RuntimeFlowgraph(
        flowgraph,
        from_steps=chip.get('option', 'from'),
        to_steps=chip.get('option', 'to'))

    all_steps = [step for step, index in runtime_no_prune.get_exit_nodes()
                 if (step, index) not in chip.get('option', 'prune')]
    complete_steps = [step for step, _ in runtime.get_completed_nodes(
        record=chip.schema.get("record", field='schema'))]

    unreached = set(all_steps).difference(complete_steps)

    if unreached:
        raise SiliconCompilerError(
            f'These final steps could not be reached: {",".join(sorted(unreached))}', chip=chip)


def get_check_node_keys(chip, step, index):
    tool, task = get_tool_task(chip, step, index)

    # Collect keys to check for changes
    required = chip.get('tool', tool, 'task', task, 'require', step=step, index=index)

    tool_task_key = ('tool', tool, 'task', task)
    for key in ('option', 'threads', 'prescript', 'postscript', 'refdir', 'script',):
        required.append(",".join([*tool_task_key, key]))

    for env_key in chip.getkeys(*tool_task_key, 'env'):
        required.append(",".join([*tool_task_key, 'env', env_key]))

    return set(sorted(required))


def check_node_inputs(chip, step, index):
    from siliconcompiler import Chip  # import here to avoid circular import

    if chip.get('option', 'clean'):
        return True

    def get_file_time(path):
        times = [os.path.getmtime(path)]
        if os.path.isdir(path):
            for path_root, _, files in os.walk(path):
                for path_end in files:
                    times.append(os.path.getmtime(os.path.join(path_root, path_end)))

        return max(times)

    # Load previous manifest
    input_manifest = None
    in_cfg = f"{chip.getworkdir(step=step, index=index)}/inputs/{chip.design}.pkg.json"
    if os.path.exists(in_cfg):
        input_manifest_time = get_file_time(in_cfg)
        input_manifest = Schema(manifest=in_cfg, logger=chip.logger)

    if not input_manifest:
        # No manifest found so assume okay
        return True

    flow = chip.get('option', 'flow')
    input_flow = input_manifest.get('option', 'flow')

    # Assume modified if flow does not match
    if flow != input_flow:
        return False

    input_chip = Chip('<>')
    input_chip.schema = input_manifest
    # Copy over useful information from chip
    input_chip.logger = chip.logger
    input_chip._packages = chip._packages

    tool, task = get_tool_task(chip, step, index)
    input_tool, input_task = get_tool_task(input_chip, step, index)

    # Assume modified if tool or task does not match
    if tool != input_tool or task != input_task:
        return False

    # Check if inputs changed
    new_inputs = set(_select_inputs(chip, step, index, trial=True))
    if set(input_chip.get('record', 'inputnode', step=step, index=index)) != new_inputs:
        chip.logger.warning(f'inputs to {step}{index} has been modified from previous run')
        return False

    # Collect keys to check for changes
    required = get_check_node_keys(chip, step, index)
    required.update(get_check_node_keys(input_chip, step, index))

    def print_warning(key, extra=None):
        if extra:
            chip.logger.warning(f'[{",".join(key)}] ({extra}) in {step}{index} has been modified '
                                'from previous run')
        else:
            chip.logger.warning(f'[{",".join(key)}] in {step}{index} has been modified '
                                'from previous run')

    # Check if keys have been modified
    for check_key in required:
        key = check_key.split(',')

        if not chip.valid(*key) or not input_chip.valid(*key):
            print_warning(key)
            return False

        check_step = step
        check_index = index
        if chip.get(*key, field='pernode').is_never():
            check_step = None
            check_index = None

        sc_type = chip.get(*key, field='type')
        if 'file' in sc_type or 'dir' in sc_type:
            if chip.get('option', 'hash') and input_chip.get('option', 'hash'):
                check_hash = chip.hash_files(*key, update=False, check=False,
                                             verbose=False, allow_cache=True,
                                             step=check_step, index=check_index)
                prev_hash = input_chip.get(*key, field='filehash',
                                           step=check_step, index=check_index)

                if check_hash != prev_hash:
                    print_warning(key, "file hash")
                    return False
            else:
                # check timestamps on current files
                for check_file in chip.find_files(*key, step=check_step, index=check_index):
                    if get_file_time(check_file) > input_manifest_time:
                        print_warning(key, "timestamp")
                        return False

                # check values
                for field in ('value', 'package'):
                    check_val = chip.get(*key, field=field, step=check_step, index=check_index)
                    prev_val = input_chip.get(*key, field=field, step=check_step, index=check_index)

                    if check_val != prev_val:
                        print_warning(key)
                        return False
        else:
            check_val = chip.get(*key, step=check_step, index=check_index)
            prev_val = input_chip.get(*key, step=check_step, index=check_index)

            if check_val != prev_val:
                print_warning(key)
                return False

    return True


###########################################################################
def check_logfile(chip, jobname=None, step=None, index='0',
                  logfile=None, display=True):
    '''
    Checks logfile for patterns found in the 'regex' parameter.

    Reads the content of the task's log file and compares the content found
    with the task's 'regex' parameter. The matches are stored in the file
    '<step>.<suffix>' in the current directory. The matches are logged
    if display is set to True.

    Args:
        jobname (str): Job directory name. If None, :keypath:`option, jobname` is used.
        step (str): Task step name ('syn', 'place', etc). If None, :keypath:`arg, step` is used.
        index (str): Task index. Default value is 0. If None, :keypath:`arg, index` is used.
        logfile (str): Path to logfile. If None, the default task logfile is used.
        display (bool): If True, logs matches.

    Returns:
        Dictionary mapping suffixes to number of matches for that suffix's
        regex.

    Examples:
        >>> chip.check_logfile(step='place')
        Searches for regex matches in the place logfile.
    '''

    # Using manifest to get defaults

    flow = chip.get('option', 'flow')

    if jobname is None:
        jobname = chip.get('option', 'jobname')
    if step is None:
        step = chip.get('arg', 'step')
        if step is None:
            raise ValueError("Must provide 'step' or set ['arg', 'step']")
    if index is None:
        index = chip.get('arg', 'index')
        if index is None:
            raise ValueError("Must provide 'index' or set ['arg', 'index']")
    if logfile is None:
        logfile = os.path.join(chip.getworkdir(jobname=jobname, step=step, index=index),
                               f'{step}.log')

    tool, task = get_tool_task(chip, step, index, flow=flow)

    # Creating local dictionary (for speed)
    # chip.get is slow
    checks = {}
    matches = {}
    for suffix in chip.getkeys('tool', tool, 'task', task, 'regex'):
        regexes = chip.get('tool', tool, 'task', task, 'regex', suffix, step=step, index=index)
        if not regexes:
            continue

        checks[suffix] = {}
        checks[suffix]['report'] = open(f"{step}.{suffix}", "w")
        checks[suffix]['args'] = regexes
        matches[suffix] = 0

    # Order suffixes as follows: [..., 'warnings', 'errors']
    ordered_suffixes = list(filter(lambda key:
                                   key not in ['warnings', 'errors'], checks.keys()))
    if 'warnings' in checks:
        ordered_suffixes.append('warnings')
    if 'errors' in checks:
        ordered_suffixes.append('errors')

    # Looping through patterns for each line
    with sc_open(logfile) as f:
        line_count = sum(1 for _ in f)
        right_align = len(str(line_count))
        for suffix in ordered_suffixes:
            # Start at the beginning of file again
            f.seek(0)
            for num, line in enumerate(f, start=1):
                string = line
                for item in checks[suffix]['args']:
                    if string is None:
                        break
                    else:
                        string = utils.grep(chip, item, string)
                if string is not None:
                    matches[suffix] += 1
                    # always print to file
                    line_with_num = f'{num: >{right_align}}: {string.strip()}'
                    print(line_with_num, file=checks[suffix]['report'])
                    # selectively print to display
                    if display:
                        if suffix == 'errors':
                            chip.logger.error(line_with_num)
                        elif suffix == 'warnings':
                            chip.logger.warning(line_with_num)
                        else:
                            chip.logger.info(f'{suffix}: {line_with_num}')

    for suffix in ordered_suffixes:
        checks[suffix]['report'].close()

    return matches


def copy_old_run_dir(chip, org_jobname):
    from_nodes = []
    flow = chip.get('option', 'flow')
    for step in chip.get('option', 'from'):
        from_nodes.extend(
            [(step, index) for index in chip.getkeys('flowgraph', flow, step)])
    from_nodes = set(from_nodes)
    if not from_nodes:
        # Nothing to do
        return

    if org_jobname == chip.get('option', 'jobname'):
        return

    # Copy nodes forward
    runtime = RuntimeFlowgraph(
        chip.schema.get("flowgraph", flow, field="schema"),
        to_steps=chip.get('option', 'from'),
        prune_nodes=chip.get('option', 'prune'))
    org_nodes = set(runtime.get_nodes())

    copy_nodes = org_nodes.difference(from_nodes)

    def copy_files(from_path, to_path):
        shutil.copytree(from_path, to_path,
                        dirs_exist_ok=True,
                        copy_function=utils.link_copy)

    for step, index in copy_nodes:
        copy_from = chip.getworkdir(jobname=org_jobname, step=step, index=index)
        copy_to = chip.getworkdir(step=step, index=index)

        if not os.path.exists(copy_from):
            continue

        chip.logger.info(f'Importing {step}{index} from {org_jobname}')
        copy_files(copy_from, copy_to)

    # Copy collect directory
    copy_from = chip._getcollectdir(jobname=org_jobname)
    copy_to = chip._getcollectdir()
    if os.path.exists(copy_from):
        copy_files(copy_from, copy_to)

    # Modify manifests to correct jobname
    for step, index in copy_nodes:
        tool, _ = get_tool_task(chip, step, index)
        task_class = chip.get("tool", tool, field="schema")

        # rewrite replay files
        replay_file = f'{chip.getworkdir(step=step, index=index)}/replay.sh'
        if os.path.exists(replay_file):
            # delete file as it might be a hard link
            os.remove(replay_file)
            chip.set('arg', 'step', step)
            chip.set('arg', 'index', index)
            task_class.set_runtime(chip, step=step, index=index)
            task_class.generate_replay_script(replay_file, chip.getworkdir(step=step, index=index))
            task_class.set_runtime(None)
            chip.unset('arg', 'step')
            chip.unset('arg', 'index')

        for io in ('inputs', 'outputs'):
            manifest = f'{chip.getworkdir(step=step, index=index)}/{io}/{chip.design}.pkg.json'
            if os.path.exists(manifest):
                schema = Schema(manifest=manifest)
                # delete file as it might be a hard link
                os.remove(manifest)
                schema.set('option', 'jobname', chip.get('option', 'jobname'))
                schema.write_manifest(manifest)


def clean_node_dir(chip, step, index):
    node_dir = chip.getworkdir(step=step, index=index)
    if os.path.isdir(node_dir):
        shutil.rmtree(node_dir)


def clean_build_dir(chip):
    if chip.get('record', 'remoteid'):
        return

    if chip.get('arg', 'step'):
        return

    if chip.get('option', 'clean') and not chip.get('option', 'from'):
        # If no step or nodes to start from were specified, the whole flow is being run
        # start-to-finish. Delete the build dir to clear stale results.
        cur_job_dir = chip.getworkdir()
        if os.path.isdir(cur_job_dir):
            shutil.rmtree(cur_job_dir)

        return

    if chip.get('option', 'from'):
        runtime = RuntimeFlowgraph(
            chip.schema.get("flowgraph", chip.get('option', 'flow'), field='schema'),
            from_steps=chip.get('option', 'from'),
            to_steps=chip.get('option', 'to'),
            prune_nodes=chip.get('option', 'prune'))
        # Remove stale outputs that will be rerun
        for step, index in runtime.get_nodes():
            clean_node_dir(chip, step, index)

    all_nodes = set(chip.schema.get("flowgraph", chip.get('option', 'flow'),
                                    field="schema").get_nodes())
    old_nodes = __collect_nodes_in_workdir(chip)
    node_mismatch = old_nodes.difference(all_nodes)
    if node_mismatch:
        # flow has different structure so clear whole
        cur_job_dir = chip.getworkdir()
        shutil.rmtree(cur_job_dir)


def __collect_nodes_in_workdir(chip):
    workdir = chip.getworkdir()
    if not os.path.isdir(workdir):
        return set()

    collect_dir = chip._getcollectdir()

    nodes = []
    for step in os.listdir(workdir):
        step_dir = os.path.join(workdir, step)

        if step_dir == collect_dir:
            continue

        if not os.path.isdir(step_dir):
            continue

        for index in os.listdir(step_dir):
            if os.path.isdir(os.path.join(step_dir, index)):
                nodes.append((step, index))

    return set(nodes)


###########################################################################
def _check_manifest_dynamic(chip, step, index):
    '''Runtime checks called from _runtask().

    - Make sure expected inputs exist.
    - Make sure all required filepaths resolve correctly.
    '''
    error = False

    flow = chip.get('option', 'flow')
    tool, task = get_tool_task(chip, step, index, flow=flow)

    required_inputs = chip.get('tool', tool, 'task', task, 'input', step=step, index=index)
    input_dir = os.path.join(chip.getworkdir(step=step, index=index), 'inputs')
    for filename in required_inputs:
        path = os.path.join(input_dir, filename)
        if not os.path.exists(path):
            chip.logger.error(f'Required input {filename} not received for {step}{index}.')
            error = True

    all_required = chip.get('tool', tool, 'task', task, 'require', step=step, index=index)
    for item in all_required:
        keypath = item.split(',')
        if not chip.valid(*keypath):
            chip.logger.error(f'Cannot resolve required keypath {keypath}.')
            error = True
        else:
            paramtype = chip.get(*keypath, field='type')
            is_perstep = not chip.get(*keypath, field='pernode').is_never()
            if ('file' in paramtype) or ('dir' in paramtype):
                for val, check_step, check_index in chip.schema.get(*keypath,
                                                                    field=None).getvalues():
                    if is_perstep:
                        if check_step is None:
                            check_step = Schema.GLOBAL_KEY
                        if check_index is None:
                            check_index = Schema.GLOBAL_KEY
                    abspath = chip.find_files(*keypath,
                                              missing_ok=True,
                                              step=check_step, index=check_index)
                    unresolved_paths = val
                    if not isinstance(abspath, list):
                        abspath = [abspath]
                        unresolved_paths = [unresolved_paths]
                    for i, path in enumerate(abspath):
                        if path is None:
                            unresolved_path = unresolved_paths[i]
                            chip.logger.error(f'Cannot resolve path {unresolved_path} in '
                                              f'required file keypath {keypath}.')
                            error = True

    return not error


#######################################
def _clear_metric(chip, step, index, metric):
    '''
    Helper function to clear metrics records
    '''

    flow = chip.get('option', 'flow')
    tool, task = get_tool_task(chip, step, index, flow=flow)

    chip.unset('tool', tool, 'task', task, 'report', metric, step=step, index=index)
