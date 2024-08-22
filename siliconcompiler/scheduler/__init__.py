import copy
import distro
import getpass
import multiprocessing
import os
import platform
import psutil
import socket
import re
import shlex
import shutil
import subprocess
import sys
import time
import packaging.version
import packaging.specifiers
from io import StringIO
import traceback
from datetime import datetime
from siliconcompiler import sc_open
from siliconcompiler import utils
from siliconcompiler import _metadata
from siliconcompiler.remote import client
from siliconcompiler.schema import Schema
from siliconcompiler.scheduler import slurm
from siliconcompiler.scheduler import docker_runner
from siliconcompiler import NodeStatus, SiliconCompilerError
from siliconcompiler.flowgraph import _get_flowgraph_nodes, _get_flowgraph_execution_order, \
    _get_pruned_node_inputs, _get_flowgraph_node_inputs, _get_flowgraph_entry_nodes, \
    _unreachable_steps_to_execute, _nodes_to_execute, \
    get_nodes_from, nodes_to_execute, _check_flowgraph
from siliconcompiler.tools._common import input_file_node_name
import lambdapdk
from siliconcompiler.tools._common import get_tool_task, record_metric
from siliconcompiler.scheduler import send_messages

try:
    import resource
except ModuleNotFoundError:
    resource = None


# callback hooks to help custom runners track progress
_callback_funcs = {}


def register_callback(hook, func):
    _callback_funcs[hook] = func


def _get_callback(hook):
    if hook in _callback_funcs:
        return _callback_funcs[hook]
    return None


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

    # Check if flowgraph is complete and valid
    flow = chip.get('option', 'flow')
    if not _check_flowgraph(chip, flow=flow):
        raise SiliconCompilerError(
            f"{flow} flowgraph contains errors and cannot be run.",
            chip=chip)

    copy_old_run_dir(chip, org_jobname)
    clean_build_dir(chip)
    _reset_flow_nodes(chip, flow, nodes_to_execute(chip, flow))

    # Save current environment
    environment = copy.deepcopy(os.environ)
    # Set env variables
    for envvar in chip.getkeys('option', 'env'):
        val = chip.get('option', 'env', envvar)
        os.environ[envvar] = val

    if chip.get('option', 'remote'):
        client.remote_process(chip)
    else:
        _local_process(chip, flow)

    # Merge cfgs from last executed tasks, and write out a final manifest.
    _finalize_run(chip, environment)


###########################################################################
def _finalize_run(chip, environment):
    '''
    Helper function to finalize a job run after it completes:
    * Restore any environment variable changes made during the run.
    * Clear any -arg_step/-arg_index values in case only one node was run.
    * Store this run in the Schema's 'history' field.
    * Write out a final JSON manifest containing the full results and history.
    '''

    # Restore environment
    os.environ.clear()
    os.environ.update(environment)

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

    if chip.get('option', 'clean') or not chip.get('option', 'from'):
        load_nodes = _get_flowgraph_nodes(chip, flow)
    else:
        for step in chip.get('option', 'from'):
            from_nodes.extend(
                [(step, index) for index in chip.getkeys('flowgraph', flow, step)])

        load_nodes = _nodes_to_execute(
            chip,
            flow,
            _get_flowgraph_entry_nodes(chip, flow),
            from_nodes,
            chip.get('option', 'prune'))

    for node_level in _get_flowgraph_execution_order(chip, flow):
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
                    extra_setup_nodes[(step, index)] = Schema(manifest=manifest, logger=chip.logger)
                except Exception:
                    pass

    # Setup tools for all nodes to run.
    nodes = nodes_to_execute(chip, flow)
    all_setup_nodes = nodes + load_nodes + list(extra_setup_nodes.keys())
    for layer_nodes in _get_flowgraph_execution_order(chip, flow):
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
                        chip.set('record', 'status', node_status, step=step, index=index)

    def mark_pending(step, index):
        chip.set('record', 'status', NodeStatus.PENDING, step=step, index=index)
        for next_step, next_index in get_nodes_from(chip, flow, [(step, index)]):
            if chip.get('record', 'status', step=next_step, index=next_index) == \
                    NodeStatus.SKIPPED:
                continue

            # Mark following steps as pending
            chip.set('record', 'status', NodeStatus.PENDING, step=next_step, index=next_index)

    # Check if nodes have been modified from previous data
    for layer_nodes in _get_flowgraph_execution_order(chip, flow):
        for step, index in layer_nodes:
            # Only look at successful nodes
            if chip.get('record', 'status', step=step, index=index) not in \
                    (NodeStatus.SUCCESS, NodeStatus.SKIPPED):
                continue

            if not check_node_inputs(chip, step, index):
                # change failing nodes to pending
                mark_pending(step, index)
            elif (step, index) in extra_setup_nodes:
                # import old information
                chip.schema._import_journal(extra_setup_nodes[(step, index)])

    # Ensure pending nodes cause following nodes to be run
    for step, index in nodes:
        if chip.get('record', 'status', step=step, index=index) in \
                (NodeStatus.PENDING, NodeStatus.ERROR):
            mark_pending(step, index)

    # Clean nodes marked pending
    for step, index in nodes:
        if chip.get('record', 'status', step=step, index=index) == NodeStatus.PENDING:
            clean_node_dir(chip, step, index)

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

    nodes_to_run = {}
    processes = {}
    local_processes = []
    _prepare_nodes(chip, nodes_to_run, processes, local_processes, flow)
    try:
        _launch_nodes(chip, nodes_to_run, processes, local_processes)
    except KeyboardInterrupt:
        # exit immediately
        sys.exit(0)

    if _get_callback('post_run'):
        _get_callback('post_run')(chip)

    _check_nodes_status(chip, flow)


def __is_posix():
    return sys.platform != 'win32'


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

    # Run node setup.
    setup_ret = None
    try:
        setup_step = getattr(chip._get_task_module(step, index), 'setup', None)
    except SiliconCompilerError:
        setup_step = None
    if setup_step:
        try:
            chip.logger.info(f'Setting up node {step}{index} with {tool}/{task}')
            setup_ret = setup_step(chip)
        except Exception as e:
            chip.logger.error(f'Failed to run setup() for {tool}/{task}')
            raise e
    else:
        raise SiliconCompilerError(f'setup() not found for tool {tool}, task {task}', chip=chip)

    # Need to restore step/index, otherwise we will skip setting up other indices.
    chip.set('option', 'flow', preset_flow)
    chip.set('arg', 'step', preset_step)
    chip.set('arg', 'index', preset_index)

    if setup_ret is not None:
        chip.logger.warning(f'Removing {step}{index} due to {setup_ret}')
        chip.set('record', 'status', NodeStatus.SKIPPED, step=step, index=index)

        return False

    return True


def _check_version(chip, reported_version, tool, step, index):
    # Based on regex for deprecated "legacy specifier" from PyPA packaging
    # library. Use this to parse PEP-440ish specifiers with arbitrary
    # versions.
    _regex_str = r"""
        (?P<operator>(==|!=|<=|>=|<|>|~=))
        \s*
        (?P<version>
            [^,;\s)]* # Since this is a "legacy" specifier, and the version
                      # string can be just about anything, we match everything
                      # except for whitespace, a semi-colon for marker support,
                      # a closing paren since versions can be enclosed in
                      # them, and a comma since it's a version separator.
        )
        """
    _regex = re.compile(r"^\s*" + _regex_str + r"\s*$", re.VERBOSE | re.IGNORECASE)

    normalize_version = getattr(chip._get_tool_module(step, index), 'normalize_version', None)
    # Version is good if it matches any of the specifier sets in this list.
    spec_sets = chip.get('tool', tool, 'version', step=step, index=index)
    if not spec_sets:
        return True

    for spec_set in spec_sets:
        split_specs = [s.strip() for s in spec_set.split(",") if s.strip()]
        specs_list = []
        for spec in split_specs:
            match = re.match(_regex, spec)
            if match is None:
                chip.logger.warning(f'Invalid version specifier {spec}. '
                                    f'Defaulting to =={spec}.')
                operator = '=='
                spec_version = spec
            else:
                operator = match.group('operator')
                spec_version = match.group('version')
            specs_list.append((operator, spec_version))

        if normalize_version is None:
            normalized_version = reported_version
            normalized_specs = ','.join([f'{op}{ver}' for op, ver in specs_list])
        else:
            try:
                normalized_version = normalize_version(reported_version)
            except Exception as e:
                chip.logger.error(f'Unable to normalize version for {tool}: {reported_version}')
                raise e
            normalized_spec_list = [f'{op}{normalize_version(ver)}' for op, ver in specs_list]
            normalized_specs = ','.join(normalized_spec_list)

        try:
            version = packaging.version.Version(normalized_version)
        except packaging.version.InvalidVersion:
            chip.logger.error(f'Version {reported_version} reported by {tool} does '
                              'not match standard.')
            if normalize_version is None:
                chip.logger.error('Tool driver should implement normalize_version().')
            else:
                chip.logger.error('normalize_version() returned '
                                  f'invalid version {normalized_version}')

            return False

        try:
            spec_set = packaging.specifiers.SpecifierSet(normalized_specs)
        except packaging.specifiers.InvalidSpecifier:
            chip.logger.error(f'Version specifier set {normalized_specs} '
                              'does not match standard.')
            return False

        if version in spec_set:
            return True

    allowedstr = '; '.join(spec_sets)
    chip.logger.error(f"Version check failed for {tool}. Check installation.")
    chip.logger.error(f"Found version {reported_version}, "
                      f"did not satisfy any version specifier set {allowedstr}.")
    return False


###########################################################################
def _runtask(chip, flow, step, index, exec_func, replay=False):
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

    chip.set('arg', 'step', step, clobber=True)
    chip.set('arg', 'index', index, clobber=True)

    chip.schema._start_journal()

    # Make record of sc version and machine
    __record_version(chip, step, index)
    # Record user information if enabled
    if chip.get('option', 'track', step=step, index=index):
        __record_usermachine(chip, step, index)

    # Start wall timer
    wall_start = time.time()
    __record_time(chip, step, index, wall_start, 'start')

    workdir = _setup_workdir(chip, step, index, replay)
    cwd = os.getcwd()
    os.chdir(workdir)

    chip._add_file_logger(os.path.join(workdir, f'sc_{step}{index}.log'))

    try:
        _setupnode(chip, flow, step, index, replay)

        exec_func(chip, step, index, replay)
    except Exception as e:
        print_traceback(chip, e)
        _haltstep(chip, chip.get('option', 'flow'), step, index)

    # return to original directory
    os.chdir(cwd)
    chip.schema._stop_journal()


###########################################################################
def _haltstep(chip, flow, step, index, log=True):
    chip.set('record', 'status', NodeStatus.ERROR, step=step, index=index)
    chip.write_manifest(os.path.join("outputs", f"{chip.get('design')}.pkg.json"))

    if log:
        chip.logger.error(f"Halting step '{step}' index '{index}' due to errors.")
        send_messages.send(chip, "fail", step, index)
    sys.exit(1)


def _setupnode(chip, flow, step, index, replay):
    _hash_files(chip, step, index, setup=True)

    # Write manifest prior to step running into inputs
    chip.write_manifest(f'inputs/{chip.get("design")}.pkg.json')

    _select_inputs(chip, step, index)
    _copy_previous_steps_output_data(chip, step, index, replay)

    # Check manifest
    if not _check_manifest_dynamic(chip, step, index):
        chip.logger.error("Fatal error in check_manifest()! See previous errors.")
        _haltstep(chip, flow, step, index)


###########################################################################
def _write_task_manifest(chip, tool, path=None, backup=True):
    suffix = chip.get('tool', tool, 'format')
    if suffix:
        manifest_path = f"sc_manifest.{suffix}"
        if path:
            manifest_path = os.path.join(path, manifest_path)

        if backup and os.path.exists(manifest_path):
            shutil.copyfile(manifest_path, f'{manifest_path}.bak')

        chip.write_manifest(manifest_path, abspath=True)


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


def _select_inputs(chip, step, index):

    flow = chip.get('option', 'flow')
    tool, _ = get_tool_task(chip, step, index, flow)
    sel_inputs = []

    select_inputs = getattr(chip._get_task_module(step, index, flow=flow),
                            '_select_inputs',
                            None)
    if select_inputs:
        sel_inputs = select_inputs(chip, step, index)
    else:
        sel_inputs = _get_flowgraph_node_inputs(chip, flow, (step, index))

    if (step, index) not in _get_flowgraph_entry_nodes(chip, flow) and not sel_inputs:
        chip.logger.error(f'No inputs selected after running {tool}')
        _haltstep(chip, flow, step, index)

    chip.set('record', 'inputnode', sel_inputs, step=step, index=index)


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
    if not _get_pruned_node_inputs(chip, flow, (step, index)):
        all_inputs = []
    elif not chip.get('record', 'inputnode', step=step, index=index):
        all_inputs = _get_pruned_node_inputs(chip, flow, (step, index))
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

            for outfile in os.scandir(f"{in_workdir}/outputs"):
                new_name = input_file_node_name(outfile.name, in_step, in_index)
                if strict:
                    if outfile.name not in in_files and new_name not in in_files:
                        continue

                copy_output_file(chip, outfile)

                if new_name in in_files:
                    # perform rename
                    os.rename(f'inputs/{outfile.name}', f'inputs/{new_name}')


def __read_std_streams(chip, quiet, is_stdout_log, stdout_reader, is_stderr_log, stderr_reader):
    '''
    Handle directing tool outputs to logger
    '''
    if not quiet:
        if is_stdout_log:
            for line in stdout_reader.readlines():
                chip.logger.info(line.rstrip())
        if is_stderr_log:
            for line in stderr_reader.readlines():
                chip.logger.error(line.rstrip())


############################################################################
# Chip helper Functions
############################################################################
def _getexe(chip, tool, step, index):
    path = chip.get('tool', tool, 'path', step=step, index=index)
    exe = chip.get('tool', tool, 'exe')
    if exe is None:
        return None

    syspath = os.getenv('PATH', os.defpath)
    if path:
        # Prepend 'path' schema var to system path
        syspath = utils._resolve_env_vars(chip, path) + os.pathsep + syspath

    fullexe = shutil.which(exe, path=syspath)

    return fullexe


#######################################
def _makecmd(chip, tool, task, step, index, script_name='replay.sh', include_path=True):
    '''
    Constructs a subprocess run command based on eda tool setup.
    Creates a replay script in current directory.

    Returns:
        runnable command (list)
        printable command (str)
        command name (str)
        command arguments (list)
    '''

    fullexe = _getexe(chip, tool, step, index)

    is_posix = __is_posix()

    def parse_options(options):
        if not options:
            return []
        shlex_opts = []
        for option in options:
            option = option.strip()
            if (option.startswith("\"") and option.endswith("\"")) or \
               (option.startswith("'") and option.endswith("'")):
                # Make sure strings are quoted in double quotes
                shlex_opts.append(f'"{option[1:-1]}"')
            else:
                shlex_opts.extend(shlex.split(option, posix=is_posix))
        return shlex_opts

    # Add scripts files
    scripts = chip.find_files('tool', tool, 'task', task, 'script', step=step, index=index)

    cmdlist = [fullexe]
    cmdlist.extend(parse_options(chip.get('tool', tool, 'task', task, 'option',
                                          step=step, index=index)))
    cmdlist.extend(scripts)

    runtime_options = getattr(chip._get_task_module(step, index), 'runtime_options', None)
    if not runtime_options:
        runtime_options = getattr(chip._get_tool_module(step, index), 'runtime_options', None)
    if runtime_options:
        try:
            cmdlist.extend(parse_options(runtime_options(chip)))
        except Exception as e:
            chip.logger.error(f'Failed to get runtime options for {tool}/{task}')
            raise e

    envvars = {}
    for key in chip.getkeys('option', 'env'):
        envvars[key] = chip.get('option', 'env', key)
    for item in chip.getkeys('tool', tool, 'licenseserver'):
        license_file = chip.get('tool', tool, 'licenseserver', item, step=step, index=index)
        if license_file:
            envvars[item] = ':'.join(license_file)

    if include_path:
        path = chip.get('tool', tool, 'path', step=step, index=index)
        if path:
            envvars['PATH'] = path + os.pathsep + os.environ['PATH']
        else:
            envvars['PATH'] = os.environ['PATH']

        # Forward additional variables
        for var in ('LD_LIBRARY_PATH',):
            val = os.getenv(var, None)
            if val:
                envvars[var] = val

    for key in chip.getkeys('tool', tool, 'task', task, 'env'):
        val = chip.get('tool', tool, 'task', task, 'env', key, step=step, index=index)
        if val:
            envvars[key] = val

    # Separate variables to be able to display nice name of executable
    cmd = os.path.basename(cmdlist[0])
    cmd_args = cmdlist[1:]
    print_cmd = " ".join([cmd, *cmd_args])
    cmdlist = [cmdlist[0]]
    for arg in cmd_args:
        if arg.startswith("\"") and arg.endswith("\""):
            # Remove quoting since subprocess will handle that for us
            cmdlist.append(arg[1:-1])
        else:
            cmdlist.append(arg)

    # create replay file
    with open(script_name, 'w') as f:
        print('#!/usr/bin/env bash', file=f)

        envvar_cmd = 'export'
        for key, val in envvars.items():
            print(f'{envvar_cmd} {key}="{val}"', file=f)

        # Ensure execution runs from the same directory
        work_dir = chip.getworkdir(step=step, index=index)
        if chip._relative_path:
            work_dir = os.path.relpath(work_dir, chip._relative_path)
        print(f'cd {work_dir}', file=f)

        format_cmd = [chip.get('tool', tool, 'exe')]
        arg_test = re.compile(r'^[-+]')
        file_test = re.compile(r'^[/]')
        for cmdarg in cmd_args:
            add_new_line = len(format_cmd) == 1

            if arg_test.match(cmdarg) or file_test.match(cmdarg):
                add_new_line = True
            else:
                if not arg_test.match(format_cmd[-1]):
                    add_new_line = True

            if add_new_line:
                format_cmd.append(cmdarg)
            else:
                format_cmd[-1] += f' {cmdarg}'
        print(" \\\n    ".join(format_cmd), file=f)

    os.chmod(script_name, 0o755)

    return cmdlist, print_cmd, cmd, cmd_args


def _run_executable_or_builtin(chip, step, index, version, toolpath, workdir, run_func=None):
    '''
    Run executable (or copy inputs to outputs for builtin functions)
    '''

    flow = chip.get('option', 'flow')
    top = chip.top()
    tool, task = get_tool_task(chip, step, index, flow)

    quiet = (
        chip.get('option', 'quiet', step=step, index=index) and not
        chip.get('option', 'breakpoint', step=step, index=index)
    )

    # TODO: Currently no memory usage tracking in breakpoints, builtins, or unexpected errors.
    max_mem_bytes = 0

    retcode = 0
    cmdlist = []
    cmd_args = []
    if run_func:
        logfile = None
        try:
            retcode = run_func(chip)
        except Exception as e:
            chip.logger.error(f'Failed in run() for {tool}/{task}: {e}')
            retcode = 1  # default to non-zero
            print_traceback(chip, e)
            chip._error = True
        finally:
            try:
                if resource:
                    # Since memory collection is not possible, collect the current process
                    # peak memory
                    max_mem_bytes = max(
                        max_mem_bytes,
                        1024 * resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            except (OSError, ValueError, PermissionError):
                pass
    else:
        cmdlist, printable_cmd, _, cmd_args = _makecmd(chip, tool, task, step, index)

        ##################
        # Make record of tool options
        __record_tool(chip, step, index, version, toolpath, cmd_args)

        chip.logger.info('Running in %s', workdir)
        chip.logger.info('%s', printable_cmd)
        timeout = chip.get('option', 'timeout', step=step, index=index)
        logfile = step + '.log'
        if sys.platform in ('darwin', 'linux') and \
           chip.get('option', 'breakpoint', step=step, index=index):
            # When we break on a step, the tool often drops into a shell.
            # However, our usual subprocess scheme seems to break terminal
            # echo for some tools. On POSIX-compatible systems, we can use
            # pty to connect the tool to our terminal instead. This code
            # doesn't handle quiet/timeout logic, since we don't want either
            # of these features for an interactive session. Logic for
            # forwarding to file based on
            # https://docs.python.org/3/library/pty.html#example.
            with open(logfile, 'wb') as log_writer:
                def read(fd):
                    data = os.read(fd, 1024)
                    log_writer.write(data)
                    return data
                import pty  # Note: this import throws exception on Windows
                retcode = pty.spawn(cmdlist, read)
        else:
            stdout_file = ''
            stdout_suffix = chip.get('tool', tool, 'task', task, 'stdout', 'suffix',
                                     step=step, index=index)
            stdout_destination = chip.get('tool', tool, 'task', task, 'stdout', 'destination',
                                          step=step, index=index)
            if stdout_destination == 'log':
                stdout_file = step + "." + stdout_suffix
            elif stdout_destination == 'output':
                stdout_file = os.path.join('outputs', top + "." + stdout_suffix)
            elif stdout_destination == 'none':
                stdout_file = os.devnull
            else:
                chip.logger.error(f'stdout/destination has no support for {stdout_destination}. '
                                  'Use [log|output|none].')
                _haltstep(chip, flow, step, index)

            stderr_file = ''
            stderr_suffix = chip.get('tool', tool, 'task', task, 'stderr', 'suffix',
                                     step=step, index=index)
            stderr_destination = chip.get('tool', tool, 'task', task, 'stderr', 'destination',
                                          step=step, index=index)
            if stderr_destination == 'log':
                stderr_file = step + "." + stderr_suffix
            elif stderr_destination == 'output':
                stderr_file = os.path.join('outputs', top + "." + stderr_suffix)
            elif stderr_destination == 'none':
                stderr_file = os.devnull
            else:
                chip.logger.error(f'stderr/destination has no support for {stderr_destination}. '
                                  'Use [log|output|none].')
                _haltstep(chip, flow, step, index)

            with open(stdout_file, 'w') as stdout_writer, \
                    open(stdout_file, 'r', errors='replace_with_warning') as stdout_reader, \
                    open(stderr_file, 'w') as stderr_writer, \
                    open(stderr_file, 'r', errors='replace_with_warning') as stderr_reader:
                # Use separate reader/writer file objects as hack to display
                # live output in non-blocking way, so we can monitor the
                # timeout. Based on https://stackoverflow.com/a/18422264.
                is_stdout_log = chip.get('tool', tool, 'task', task, 'stdout', 'destination',
                                         step=step, index=index) == 'log'
                is_stderr_log = stderr_destination == 'log' and stderr_file != stdout_file
                # if STDOUT and STDERR are to be redirected to the same file,
                # use a single writer
                if stderr_file == stdout_file:
                    stderr_writer.close()
                    stderr_reader.close()
                    stderr_writer = subprocess.STDOUT

                preexec_fn = None
                nice = None
                if __is_posix():
                    nice = chip.get('option', 'nice', step=step, index=index)

                    def set_nice():
                        os.nice(nice)

                    if nice:
                        preexec_fn = set_nice

                cmd_start_time = time.time()
                proc = subprocess.Popen(cmdlist,
                                        stdout=stdout_writer,
                                        stderr=stderr_writer,
                                        preexec_fn=preexec_fn)
                # How long to wait for proc to quit on ctrl-c before force
                # terminating.
                POLL_INTERVAL = 0.1
                MEMORY_WARN_LIMIT = 90
                try:
                    while proc.poll() is None:
                        # Gather subprocess memory usage.
                        try:
                            pproc = psutil.Process(proc.pid)
                            proc_mem_bytes = pproc.memory_full_info().uss
                            for child in pproc.children(recursive=True):
                                proc_mem_bytes += child.memory_full_info().uss
                            max_mem_bytes = max(max_mem_bytes, proc_mem_bytes)

                            memory_usage = psutil.virtual_memory()
                            if memory_usage.percent > MEMORY_WARN_LIMIT:
                                chip.logger.warn(
                                    f'Current system memory usage is {memory_usage.percent}%')

                                # increase limit warning
                                MEMORY_WARN_LIMIT = int(memory_usage.percent + 1)
                        except psutil.Error:
                            # Process may have already terminated or been killed.
                            # Retain existing memory usage statistics in this case.
                            pass
                        except PermissionError:
                            # OS is preventing access to this information so it cannot
                            # be collected
                            pass

                        # Loop until process terminates
                        __read_std_streams(chip,
                                           quiet,
                                           is_stdout_log, stdout_reader,
                                           is_stderr_log, stderr_reader)

                        if timeout is not None and time.time() - cmd_start_time > timeout:
                            chip.logger.error(f'Step timed out after {timeout} seconds')
                            utils.terminate_process(proc.pid)
                            raise SiliconCompilerTimeout(f'{step}{index} timeout')
                        time.sleep(POLL_INTERVAL)
                except KeyboardInterrupt:
                    kill_process(chip, proc, tool, 5 * POLL_INTERVAL, msg="Received ctrl-c. ")
                    _haltstep(chip, flow, step, index, log=False)
                except SiliconCompilerTimeout:
                    send_messages.send(chip, "timeout", step, index)
                    kill_process(chip, proc, tool, 5 * POLL_INTERVAL)
                    chip._error = True

                # Read the remaining
                __read_std_streams(chip,
                                   quiet,
                                   is_stdout_log, stdout_reader,
                                   is_stderr_log, stderr_reader)
                retcode = proc.returncode

    chip.set('record', 'toolexitcode', retcode, step=step, index=index)
    if retcode != 0:
        msg = f'Command failed with code {retcode}.'
        if logfile:
            if quiet:
                # Print last 10 lines of log when in quiet mode
                with sc_open(logfile) as logfd:
                    loglines = logfd.read().splitlines()
                    for logline in loglines[-10:]:
                        chip.logger.error(logline)
                # No log file for pure-Python tools.
            msg += f' See log file {os.path.abspath(logfile)}'
        chip.logger.warning(msg)
        chip._error = True

    # Capture memory usage
    record_metric(chip, step, index, 'memory', max_mem_bytes, source=None, source_unit='B')


def _post_process(chip, step, index):
    flow = chip.get('option', 'flow')
    tool, task = get_tool_task(chip, step, index, flow)
    func = getattr(chip._get_task_module(step, index, flow=flow), 'post_process', None)
    if func:
        try:
            func(chip)
        except Exception as e:
            chip.logger.error(f'Failed to run post-process for {tool}/{task}.')
            print_traceback(chip, e)
            chip._error = True


def _check_logfile(chip, step, index, quiet=False, run_func=None):
    '''
    Check log file (must be after post-process)
    '''
    if run_func is None:
        log_file = os.path.join(chip.getworkdir(step=step, index=index), f'{step}.log')
        matches = check_logfile(chip, step=step, index=index,
                                display=not quiet,
                                logfile=log_file)
        if 'errors' in matches:
            errors = chip.get('metric', 'errors', step=step, index=index)
            if errors is None:
                errors = 0
            errors += matches['errors']
            record_metric(chip, step, index, 'errors', errors, f'{step}.log')
        if 'warnings' in matches:
            warnings = chip.get('metric', 'warnings', step=step, index=index)
            if warnings is None:
                warnings = 0
            warnings += matches['warnings']
            record_metric(chip, step, index, 'warnings', warnings, f'{step}.log')


def _executenode(chip, step, index, replay):
    workdir = chip.getworkdir(step=step, index=index)
    flow = chip.get('option', 'flow')
    tool, _ = get_tool_task(chip, step, index, flow)

    _pre_process(chip, step, index)

    if chip.get('record', 'status', step=step, index=index) == NodeStatus.SKIPPED:
        # copy inputs to outputs and skip execution
        forward_output_files(chip, step, index)

        send_messages.send(chip, "skipped", step, index)
    else:
        _set_env_vars(chip, step, index)

        run_func = getattr(chip._get_task_module(step, index, flow=flow), 'run', None)
        (toolpath, version) = _check_tool_version(chip, step, index, run_func)

        # Write manifest (tool interface) (Don't move this!)
        _write_task_manifest(chip, tool)

        send_messages.send(chip, "begin", step, index)

        # Start CPU Timer
        chip.logger.debug("Starting executable")
        cpu_start = time.time()

        _run_executable_or_builtin(chip, step, index, version, toolpath, workdir, run_func)

        # Capture cpu runtime
        cpu_end = time.time()
        cputime = round((cpu_end - cpu_start), 2)
        record_metric(chip, step, index, 'exetime', cputime, source=None, source_unit='s')

        _post_process(chip, step, index)

    _finalizenode(chip, step, index, replay)

    send_messages.send(chip, "end", step, index)


def _pre_process(chip, step, index):
    flow = chip.get('option', 'flow')
    tool, task = get_tool_task(chip, step, index, flow)
    func = getattr(chip._get_task_module(step, index, flow=flow), 'pre_process', None)
    if func:
        try:
            func(chip)
        except Exception as e:
            chip.logger.error(f"Pre-processing failed for '{tool}/{task}'.")
            raise e
        if chip._error:
            chip.logger.error(f"Pre-processing failed for '{tool}/{task}'")
            _haltstep(chip, flow, step, index)


def _set_env_vars(chip, step, index):
    flow = chip.get('option', 'flow')
    tool, task = get_tool_task(chip, step, index, flow)
    # License file configuration.
    for item in chip.getkeys('tool', tool, 'licenseserver'):
        license_file = chip.get('tool', tool, 'licenseserver', item, step=step, index=index)
        if license_file:
            os.environ[item] = ':'.join(license_file)

    # Tool-specific environment variables for this task.
    for item in chip.getkeys('tool', tool, 'task', task, 'env'):
        val = chip.get('tool', tool, 'task', task, 'env', item, step=step, index=index)
        if val:
            os.environ[item] = val


def _check_tool_version(chip, step, index, run_func=None):
    '''
    Check exe version
    '''

    flow = chip.get('option', 'flow')
    tool, task = get_tool_task(chip, step, index, flow)

    vercheck = not chip.get('option', 'novercheck', step=step, index=index)
    veropt = chip.get('tool', tool, 'vswitch')
    exe = _getexe(chip, tool, step, index)
    version = None
    if exe is not None:
        exe_path, exe_base = os.path.split(exe)
        if veropt:
            cmdlist = [exe]
            cmdlist.extend(veropt)
            proc = subprocess.run(cmdlist,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  universal_newlines=True)
            if proc.returncode != 0:
                chip.logger.warning(f'Version check on {tool} failed with '
                                    f'code {proc.returncode}')

            parse_version = getattr(chip._get_tool_module(step, index, flow=flow),
                                    'parse_version',
                                    None)
            if parse_version is None:
                chip.logger.error(f'{tool}/{task} does not implement parse_version().')
                _haltstep(chip, flow, step, index)
            try:
                version = parse_version(proc.stdout)
            except Exception as e:
                chip.logger.error(f'{tool} failed to parse version string: {proc.stdout}')
                raise e

            chip.logger.info(f"Tool '{exe_base}' found with version '{version}' "
                             f"in directory '{exe_path}'")
            if vercheck and not _check_version(chip, version, tool, step, index):
                if proc.returncode != 0:
                    chip.logger.error(f"Tool '{exe_base}' responded with: {proc.stdout}")
                _haltstep(chip, flow, step, index)
        else:
            chip.logger.info(f"Tool '{exe_base}' found in directory '{exe_path}'")
    elif run_func is None:
        exe_base = chip.get('tool', tool, 'exe')
        chip.logger.error(f'Executable {exe_base} not found')
        _haltstep(chip, flow, step, index)
    return (exe, version)


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
                pernode = chip.get(*args, field='pernode')
                if pernode == 'never':
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
    flow = chip.get('option', 'flow')
    tool, task = get_tool_task(chip, step, index, flow)
    quiet = (
        chip.get('option', 'quiet', step=step, index=index) and not
        chip.get('option', 'breakpoint', step=step, index=index)
    )
    run_func = getattr(chip._get_task_module(step, index, flow=flow), 'run', None)

    is_skipped = chip.get('record', 'status', step=step, index=index) == NodeStatus.SKIPPED

    if not is_skipped:
        _check_logfile(chip, step, index, quiet, run_func)
    _hash_files(chip, step, index)

    # Capture wall runtime and cpu cores
    wall_end = time.time()
    __record_time(chip, step, index, wall_end, 'end')

    # calculate total time
    total_times = []
    for check_step, check_index in _get_flowgraph_nodes(chip, flow):
        total_time = chip.get('metric', 'totaltime', step=check_step, index=check_index)
        if total_time is not None:
            total_times.append(total_time)
    if total_times:
        total_time = max(total_times)
    else:
        total_time = 0.0

    walltime = wall_end - get_record_time(chip, step, index, 'starttime')
    record_metric(chip, step, index, 'tasktime', walltime,
                  source=None, source_unit='s')
    record_metric(chip, step, index, 'totaltime', total_time + walltime,
                  source=None, source_unit='s')
    chip.logger.info(f"Finished task in {round(walltime, 2)}s")

    # Save a successful manifest
    if not is_skipped:
        chip.set('record', 'status', NodeStatus.SUCCESS, step=step, index=index)
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
    from siliconcompiler.issue import generate_testcase

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


def _reset_flow_nodes(chip, flow, nodes_to_execute):
    # Reset flowgraph/records/metrics by probing build directory. We need
    # to set values to None for steps we may re-run so that merging
    # manifests from _runtask() actually updates values.

    def clear_node(step, index):
        # Reset metrics and records
        for metric in chip.getkeys('metric'):
            _clear_metric(chip, step, index, metric)
        for record in chip.getkeys('record'):
            _clear_record(chip, step, index, record, preserve=['remoteid', 'status'])

    # Mark all nodes as pending
    for step, index in _get_flowgraph_nodes(chip, flow):
        chip.set('record', 'status', NodeStatus.PENDING, step=step, index=index)

    should_resume = not chip.get('option', 'clean')
    for step, index in _get_flowgraph_nodes(chip, flow):
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
                    chip.set('record', 'status', old_status, step=step, index=index)
            except Exception:
                # unable to load so leave it default
                pass
        else:
            chip.set('record', 'status', NodeStatus.ERROR, step=step, index=index)

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


def _prepare_nodes(chip, nodes_to_run, processes, local_processes, flow):
    '''
    For each node to run, prepare a process and store its dependencies
    '''
    # Ensure we use spawn for multiprocessing so loggers initialized correctly
    multiprocessor = multiprocessing.get_context('spawn')
    init_funcs = set()
    for (step, index) in nodes_to_execute(chip, flow):
        node = (step, index)

        if chip.get('record', 'status', step=step, index=index) != NodeStatus.PENDING:
            continue

        nodes_to_run[node] = _get_pruned_node_inputs(chip, flow, (step, index))

        exec_func = _executenode

        if chip.get('option', 'scheduler', 'name', step=step, index=index) == 'slurm':
            # Defer job to compute node
            # If the job is configured to run on a cluster, collect the schema
            # and send it to a compute node for deferred execution.
            init_funcs.add(slurm.init)
            exec_func = slurm._defernode
        elif chip.get('option', 'scheduler', 'name', step=step, index=index) == 'docker':
            # Run job in docker
            init_funcs.add(docker_runner.init)
            exec_func = docker_runner.run
            local_processes.append((step, index))
        else:
            local_processes.append((step, index))

        processes[node] = multiprocessor.Process(target=_runtask,
                                                 args=(chip, flow, step, index, exec_func))

    for init_func in init_funcs:
        init_func(chip)


def _check_node_dependencies(chip, node, deps, deps_was_successful):
    had_deps = len(deps) > 0
    step, index = node
    tool, task = get_tool_task(chip, step, index)

    # Clear any nodes that have finished from dependency list.
    for in_step, in_index in list(deps):
        in_status = chip.get('record', 'status', step=in_step, index=in_index)
        if in_status != NodeStatus.PENDING:
            deps.remove((in_step, in_index))
        if in_status == NodeStatus.SUCCESS:
            deps_was_successful[node] = True
        if in_status == NodeStatus.ERROR:
            # Fail if any dependency failed for non-builtin task
            if tool != 'builtin':
                deps.clear()
                chip.set('record', 'status', NodeStatus.ERROR, step=step, index=index)
                return

    # Fail if no dependency successfully finished for builtin task
    if had_deps and len(deps) == 0 \
            and tool == 'builtin' and not deps_was_successful.get(node):
        chip.set('record', 'status', NodeStatus.ERROR, step=step, index=index)


def _launch_nodes(chip, nodes_to_run, processes, local_processes):
    running_nodes = {}
    max_parallel_run = chip.get('option', 'scheduler', 'maxnodes')
    max_threads = os.cpu_count()
    if not max_parallel_run:
        max_parallel_run = max_threads

    # clip max parallel jobs to 1 <= jobs <= max_threads
    max_parallel_run = max(1, min(max_parallel_run, max_threads))

    def allow_start(node):
        if node not in local_processes:
            # using a different scheduler, so allow
            return True, 0

        if len(running_nodes) >= max_parallel_run:
            return False, 0

        # Record thread count requested
        step, index = node
        tool, task = get_tool_task(chip, step, index)
        requested_threads = chip.get('tool', tool, 'task', task, 'threads',
                                     step=step, index=index)
        if not requested_threads:
            # not specified, marking it max to be safe
            requested_threads = max_threads
        # clamp to max_parallel to avoid getting locked up
        requested_threads = max(1, min(requested_threads, max_threads))

        if requested_threads + sum(running_nodes.values()) > max_threads:
            # delay until there are enough core available
            return False, 0

        # allow and record how many threads to associate
        return True, requested_threads

    deps_was_successful = {}

    if _get_callback('pre_run'):
        _get_callback('pre_run')(chip)

    while len(nodes_to_run) > 0 or len(running_nodes) > 0:
        _process_completed_nodes(chip, processes, running_nodes)

        # Check for new nodes that can be launched.
        for node, deps in list(nodes_to_run.items()):
            # TODO: breakpoint logic:
            # if node is breakpoint, then don't launch while len(running_nodes) > 0

            _check_node_dependencies(chip, node, deps, deps_was_successful)

            if chip.get('record', 'status', step=node[0], index=node[1]) == NodeStatus.ERROR:
                del nodes_to_run[node]
                continue

            # If there are no dependencies left, launch this node and
            # remove from nodes_to_run.
            if len(deps) == 0:
                dostart, requested_threads = allow_start(node)

                if dostart:
                    if _get_callback('pre_node'):
                        _get_callback('pre_node')(chip, *node)

                    processes[node].start()
                    del nodes_to_run[node]
                    running_nodes[node] = requested_threads

        # Check for situation where we have stuff left to run but don't
        # have any nodes running. This shouldn't happen, but we will get
        # stuck in an infinite loop if it does, so we want to break out
        # with an explicit error.
        if len(nodes_to_run) > 0 and len(running_nodes) == 0:
            raise SiliconCompilerError(
                'Nodes left to run, but no running nodes. From/to may be invalid.', chip=chip)

        # TODO: exponential back-off with max?
        time.sleep(0.1)


def _process_completed_nodes(chip, processes, running_nodes):
    for node in list(running_nodes.keys()):
        if not processes[node].is_alive():
            step, index = node
            manifest = os.path.join(chip.getworkdir(step=step, index=index),
                                    'outputs',
                                    f'{chip.design}.pkg.json')
            chip.logger.debug(f'{step}{index} is complete merging: {manifest}')
            if os.path.exists(manifest):
                chip.schema.read_journal(manifest)

            del running_nodes[node]
            if processes[node].exitcode > 0:
                status = NodeStatus.ERROR
            else:
                status = chip.get('record', 'status', step=step, index=index)
                if not status or status == NodeStatus.PENDING:
                    status = NodeStatus.ERROR

            chip.set('record', 'status', status, step=step, index=index)

            if _get_callback('post_node'):
                _get_callback('post_node')(chip, *node)


def _check_nodes_status(chip, flow):
    def success(node):
        return chip.get('record', 'status', step=node[0], index=node[1]) in \
            (NodeStatus.SUCCESS, NodeStatus.SKIPPED)

    unreachable_steps = _unreachable_steps_to_execute(chip, flow, cond=success)
    if unreachable_steps:
        raise SiliconCompilerError(
            f'These final steps could not be reached: {list(unreachable_steps)}', chip=chip)


#######################################
def __record_version(chip, step, index):
    chip.set('record', 'scversion', _metadata.version, step=step, index=index)


#######################################
def __record_time(chip, step, index, record_time, timetype):
    formatted_time = datetime.fromtimestamp(record_time).strftime('%Y-%m-%d %H:%M:%S')

    if timetype == 'start':
        key = 'starttime'
    elif timetype == 'end':
        key = 'endtime'
    else:
        raise ValueError(f'{timetype} is not a valid time record')

    chip.set('record', key, formatted_time, step=step, index=index)


def get_record_time(chip, step, index, timetype):
    return datetime.strptime(
        chip.get('record', timetype, step=step, index=index),
        '%Y-%m-%d %H:%M:%S').timestamp()


#######################################
def __record_tool(chip, step, index, toolversion=None, toolpath=None, cli_args=None):
    if toolversion:
        chip.set('record', 'toolversion', toolversion, step=step, index=index)

    if toolpath:
        chip.set('record', 'toolpath', toolpath, step=step, index=index)

    if cli_args is not None:
        toolargs = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cli_args)
        chip.set('record', 'toolargs', toolargs, step=step, index=index)


#######################################
def _get_cloud_region():
    # TODO: add logic to figure out if we're running on a remote cluster and
    # extract the region in a provider-specific way.
    return 'local'


#######################################
def __record_usermachine(chip, step, index):
    machine_info = _get_machine_info()
    chip.set('record', 'platform', machine_info['system'], step=step, index=index)

    if machine_info['distro']:
        chip.set('record', 'distro', machine_info['distro'], step=step, index=index)

    chip.set('record', 'osversion', machine_info['osversion'], step=step, index=index)

    if machine_info['kernelversion']:
        chip.set('record', 'kernelversion', machine_info['kernelversion'], step=step, index=index)

    chip.set('record', 'arch', machine_info['arch'], step=step, index=index)

    chip.set('record', 'userid', getpass.getuser(), step=step, index=index)

    chip.set('record', 'machine', platform.node(), step=step, index=index)

    chip.set('record', 'region', _get_cloud_region(), step=step, index=index)

    try:
        for interface, addrs in psutil.net_if_addrs().items():
            if interface == 'lo':
                # don't consider loopback device
                continue

            if not addrs:
                # skip missing addrs
                continue

            use_addr = False
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    if not addr.address.startswith('127.'):
                        use_addr = True
                    break

            if use_addr:
                ipaddr = None
                macaddr = None
                for addr in addrs:
                    if not ipaddr and addr.family == socket.AF_INET:
                        ipaddr = addr.address
                    if not ipaddr and addr.family == socket.AF_INET6:
                        ipaddr = addr.address
                    if not macaddr and addr.family == psutil.AF_LINK:
                        macaddr = addr.address

                chip.set('record', 'ipaddr', ipaddr, step=step, index=index)
                chip.set('record', 'macaddr', macaddr, step=step, index=index)
                break
    except:  # noqa E722
        chip.logger.warning('Could not find default network interface info')


#######################################
def _get_machine_info():
    system = platform.system()
    if system == 'Darwin':
        lower_sys_name = 'macos'
    else:
        lower_sys_name = system.lower()

    if system == 'Linux':
        distro_name = distro.id()
    else:
        distro_name = None

    if system == 'Darwin':
        osversion, _, _ = platform.mac_ver()
    elif system == 'Linux':
        osversion = distro.version()
    else:
        osversion = platform.release()

    if system == 'Linux':
        kernelversion = platform.release()
    elif system == 'Windows':
        kernelversion = platform.version()
    elif system == 'Darwin':
        kernelversion = platform.release()
    else:
        kernelversion = None

    arch = platform.machine()

    return {'system': lower_sys_name,
            'distro': distro_name,
            'osversion': osversion,
            'kernelversion': kernelversion,
            'arch': arch}


def print_traceback(chip, exception):
    chip.logger.error(f'{exception}')
    trace = StringIO()
    traceback.print_tb(exception.__traceback__, file=trace)
    chip.logger.error("Backtrace:")
    for line in trace.getvalue().splitlines():
        chip.logger.error(line)


def kill_process(chip, proc, tool, poll_interval, msg=""):
    TERMINATE_TIMEOUT = 5
    interrupt_time = time.time()
    chip.logger.info(f'{msg}Waiting for {tool} to exit...')
    while proc.poll() is None and \
            (time.time() - interrupt_time) < TERMINATE_TIMEOUT:
        time.sleep(5 * poll_interval)
    if proc.poll() is None:
        chip.logger.warning(f'{tool} did not exit within {TERMINATE_TIMEOUT} '
                            'seconds. Terminating...')
        utils.terminate_process(proc.pid)


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

    # Collect keys to check for changes
    required = chip.get('tool', tool, 'task', task, 'require', step=step, index=index)
    required.extend(input_chip.get('tool', tool, 'task', task, 'require', step=step, index=index))

    tool_task_key = ('tool', tool, 'task', task)
    for key in ('option', 'threads', 'prescript', 'postscript', 'refdir', 'script',):
        required.append(",".join([*tool_task_key, key]))
    for check_chip in (chip, input_chip):
        for env_key in chip.getkeys(*tool_task_key, 'env'):
            required.append(",".join([*tool_task_key, 'env', env_key]))

    def print_warning(key, extra=None):
        if extra:
            chip.logger.warning(f'[{",".join(key)}] ({extra}) in {step}{index} has been modified '
                                'from previous run')
        else:
            chip.logger.warning(f'[{",".join(key)}] in {step}{index} has been modified '
                                'from previous run')

    # Check if keys have been modified
    for check_key in sorted(set(required)):
        key = check_key.split(',')

        if not chip.valid(*key) or not input_chip.valid(*key):
            print_warning(key)
            return False

        pernode = chip.get(*key, field='pernode')

        check_step = step
        check_index = index
        if pernode == 'never':
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
                    print_warning(key)
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
        chip.logger.info(f'Number of {suffix}: {matches[suffix]}')
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
    org_nodes = set(_nodes_to_execute(
        chip,
        flow,
        _get_flowgraph_entry_nodes(chip, flow),
        from_nodes,
        chip.get('option', 'prune')))

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
        # rewrite replay files
        replay_file = f'{chip.getworkdir(step=step, index=index)}/replay.sh'
        if os.path.exists(replay_file):
            # delete file as it might be a hard link
            os.remove(replay_file)
            chip.set('arg', 'step', step)
            chip.set('arg', 'index', index)
            tool, task = get_tool_task(chip, step, index)
            _makecmd(chip, tool, task, step, index, script_name=replay_file)
            chip.unset('arg', 'step')
            chip.unset('arg', 'index')

        for io in ('inputs', 'outputs'):
            manifest = f'{chip.getworkdir(step=step, index=index)}/{io}/{chip.design}.pkg.json'
            if os.path.exists(manifest):
                schema = Schema(manifest=manifest)
                # delete file as it might be a hard link
                os.remove(manifest)
                schema.set('option', 'jobname', chip.get('option', 'jobname'))
                with open(manifest, 'w') as f:
                    schema.write_json(f)


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
        # Remove stale outputs that will be rerun
        for step, index in nodes_to_execute(chip):
            clean_node_dir(chip, step, index)

    all_nodes = set(_get_flowgraph_nodes(chip, flow=chip.get('option', 'flow')))
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
            is_perstep = chip.get(*keypath, field='pernode') != 'never'
            if ('file' in paramtype) or ('dir' in paramtype):
                for val, check_step, check_index in chip.schema._getvals(*keypath):
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
def _clear_metric(chip, step, index, metric, preserve=None):
    '''
    Helper function to clear metrics records
    '''

    # This function is often called in a loop; don't clear
    # metrics which the caller wants to preserve.
    if preserve and metric in preserve:
        return

    flow = chip.get('option', 'flow')
    tool, task = get_tool_task(chip, step, index, flow=flow)

    chip.unset('metric', metric, step=step, index=index)
    chip.unset('tool', tool, 'task', task, 'report', metric, step=step, index=index)


#######################################
def _clear_record(chip, step, index, record, preserve=None):
    '''
    Helper function to clear record parameters
    '''

    # This function is often called in a loop; don't clear
    # records which the caller wants to preserve.
    if preserve and record in preserve:
        return

    if chip.get('record', record, field='pernode') == 'never':
        chip.unset('record', record)
    else:
        chip.unset('record', record, step=step, index=index)
