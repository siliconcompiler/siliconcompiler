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
from siliconcompiler import NodeStatus, SiliconCompilerError
from siliconcompiler.flowgraph import _get_flowgraph_nodes, _get_flowgraph_execution_order, \
    _get_pruned_node_inputs, _get_flowgraph_node_inputs, _get_flowgraph_entry_nodes, \
    _unreachable_steps_to_execute, _get_execution_exit_nodes, _nodes_to_execute, \
    get_nodes_from
from siliconcompiler.tools._common import input_file_node_name
import lambdapdk


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
    for key in (['option', 'flow'],
                ['option', 'mode']):
        if chip.get(*key) is None:
            chip.error(f"{key} must be set before calling run()", fatal=True)

    _increment_job_name(chip)

    # Re-init logger to include run info after setting up flowgraph.
    chip._init_logger(in_run=True)

    # Check if flowgraph is complete and valid
    flow = chip.get('option', 'flow')
    if not chip._check_flowgraph(flow=flow):
        chip.error(f"{flow} flowgraph contains errors and cannot be run.", fatal=True)

    chip.clean_build_dir()
    _reset_flow_nodes(chip, flow, chip.nodes_to_execute(flow))

    # Save current environment
    environment = copy.deepcopy(os.environ)
    # Set env variables
    for envvar in chip.getkeys('option', 'env'):
        val = chip.get('option', 'env', envvar)
        os.environ[envvar] = val

    status = {}
    if chip.get('option', 'remote'):
        client.remote_process(chip)
    else:
        _local_process(chip, flow, status)

    # Merge cfgs from last executed tasks, and write out a final manifest.
    _finalize_run(chip, set(_get_execution_exit_nodes(chip, flow)), environment, status)


###########################################################################
def _finalize_run(chip, to_nodes, environment, status={}):
    '''
    Helper function to finalize a job run after it completes:
    * Merge the last-completed manifests in a job's flowgraphs.
    * Restore any environment variable changes made during the run.
    * Clear any -arg_step/-arg_index values in case only one node was run.
    * Store this run in the Schema's 'history' field.
    * Write out a final JSON manifest containing the full results and history.
    '''

    # Gather core values.
    flow = chip.get('option', 'flow')

    # Merge cfg back from last executed tasks.
    for step, index in to_nodes:
        lastdir = chip._getworkdir(step=step, index=index)

        # This no-op listdir operation is important for ensuring we have
        # a consistent view of the filesystem when dealing with NFS.
        # Without this, this thread is often unable to find the final
        # manifest of runs performed on job schedulers, even if they
        # completed successfully. Inspired by:
        # https://stackoverflow.com/a/70029046.

        dir_found = False
        try:
            os.listdir(os.path.dirname(lastdir))
            dir_found = os.path.exists(lastdir)
        except FileNotFoundError:
            dir_found = False

        lastcfg = f"{lastdir}/outputs/{chip.design}.pkg.json"
        stat_success = False
        # Determine if the task was successful, using provided status dict
        # or the node Schema if no status dict is available.
        if dir_found:
            if status:
                stat_success = (status[(step, index)] == NodeStatus.SUCCESS)
            elif os.path.isfile(lastcfg):
                schema = Schema(manifest=lastcfg)
                if schema.get('flowgraph', flow, step, index, 'status') == NodeStatus.SUCCESS:
                    stat_success = True
        if os.path.isfile(lastcfg):
            chip._read_manifest(lastcfg, clobber=False, partial=True)

        if stat_success:
            # (Status doesn't get propagated w/ "clobber=False")
            chip.set('flowgraph', flow, step, index, 'status', NodeStatus.SUCCESS)
        else:
            chip.set('flowgraph', flow, step, index, 'status', NodeStatus.ERROR)

    # Restore environment
    os.environ.clear()
    os.environ.update(environment)

    # Clear scratchpad args since these are checked on run() entry
    chip.set('arg', 'step', None, clobber=True)
    chip.set('arg', 'index', None, clobber=True)

    # Store run in history
    chip.schema.record_history()

    # Storing manifest in job root directory
    filepath = os.path.join(chip._getworkdir(), f"{chip.design}.pkg.json")
    chip.write_manifest(filepath)


def _increment_job_name(chip):
    '''
    Auto-update jobname if ['option', 'jobincr'] is True
    Do this before initializing logger so that it picks up correct jobname
    '''
    if chip.get('option', 'jobincr'):
        workdir = chip._getworkdir()
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


def _local_process(chip, flow, status):
    # Load prior nodes, if option,from is set
    if chip.get('option', 'from'):
        from_nodes = []
        for step in chip.get('option', 'from'):
            from_nodes.extend([(step, index) for index in chip.getkeys('flowgraph', flow, step)])

        load_nodes = _nodes_to_execute(
            chip,
            flow,
            _get_flowgraph_entry_nodes(chip, flow),
            from_nodes,
            chip.get('option', 'prune'))

        for step, index in load_nodes:
            if (step, index) in from_nodes:
                continue
            _merge_input_dependencies_manifests(chip, step, index, status, False)

    # Populate status dict with any flowgraph status values that have already
    # been set.
    for step, index in _get_flowgraph_nodes(chip, flow):
        node_status = chip.get('flowgraph', flow, step, index, 'status')
        if node_status is not None:
            status[(step, index)] = node_status
        else:
            status[(step, index)] = NodeStatus.PENDING

    # Setup tools for all nodes to run.
    nodes_to_execute = chip.nodes_to_execute(flow)
    for layer_nodes in _get_flowgraph_execution_order(chip, flow):
        for step, index in layer_nodes:
            if (step, index) in nodes_to_execute:
                _setup_node(chip, step, index)

    def mark_pending(step, index):
        for next_step, next_index in get_nodes_from(chip, flow, [(step, index)]):
            # Mark following steps as pending
            status[(next_step, next_index)] = NodeStatus.PENDING

    # Check if nodes have been modified from previous data
    for layer_nodes in _get_flowgraph_execution_order(chip, flow):
        for step, index in layer_nodes:
            # Only look at successful nodes
            if status[(step, index)] == NodeStatus.SUCCESS and \
               not check_node_inputs(chip, step, index):
                # change failing nodes to pending
                status[(step, index)] = NodeStatus.PENDING
                mark_pending(step, index)

    # Ensure pending nodes cause following nodes to be run
    for step, index in status:
        if status[(step, index)] == NodeStatus.PENDING:
            mark_pending(step, index)

    # Check validity of setup
    chip.logger.info("Checking manifest before running.")
    check_ok = True
    if not chip.get('option', 'skipcheck'):
        check_ok = chip.check_manifest()

    # Check if there were errors before proceeding with run
    if not check_ok:
        chip.error('Manifest check failed. See previous errors.', fatal=True)
    if chip._error:
        chip.error('Implementation errors encountered. See previous errors.', fatal=True)

    nodes_to_run = {}
    processes = {}
    local_processes = []
    _prepare_nodes(chip, nodes_to_run, processes, local_processes, flow, status)
    try:
        _launch_nodes(chip, nodes_to_run, processes, local_processes, status)
    except KeyboardInterrupt:
        # exit immediately
        sys.exit(0)

    _check_nodes_status(chip, flow, status)


def __is_posix():
    return sys.platform != 'win32'


###########################################################################
def _setup_node(chip, step, index):
    preset_step = chip.get('arg', 'step')
    preset_index = chip.get('arg', 'index')

    chip.set('arg', 'step', step)
    chip.set('arg', 'index', index)
    tool, task = chip._get_tool_task(step, index)

    # Run node setup.
    try:
        setup_step = getattr(chip._get_task_module(step, index), 'setup', None)
    except SiliconCompilerError:
        setup_step = None
    if setup_step:
        try:
            chip.logger.info(f'Setting up node {step}{index} with {tool}/{task}')
            setup_step(chip)
        except Exception as e:
            chip.logger.error(f'Failed to run setup() for {tool}/{task}')
            raise e
    else:
        chip.error(f'setup() not found for tool {tool}, task {task}', fatal=True)

    # Need to restore step/index, otherwise we will skip setting up other indices.
    chip.set('arg', 'step', preset_step)
    chip.set('arg', 'index', preset_index)


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
def _runtask(chip, flow, step, index, status, exec_func, replay=False):
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
        _setupnode(chip, flow, step, index, status, replay)

        exec_func(chip, step, index, replay)
    except Exception as e:
        print_traceback(chip, e)
        _haltstep(chip, chip.get('option', 'flow'), step, index)

    # return to original directory
    os.chdir(cwd)


###########################################################################
def _haltstep(chip, flow, step, index, log=True):
    if log:
        chip.logger.error(f"Halting step '{step}' index '{index}' due to errors.")
    chip.set('flowgraph', flow, step, index, 'status', NodeStatus.ERROR)
    chip.write_manifest(os.path.join("outputs", f"{chip.get('design')}.pkg.json"))
    sys.exit(1)


def _setupnode(chip, flow, step, index, status, replay):
    _merge_input_dependencies_manifests(chip, step, index, status, replay)

    _hash_files(chip, step, index, setup=True)

    # Write manifest prior to step running into inputs
    chip.set('arg', 'step', step, clobber=True)
    chip.set('arg', 'index', index, clobber=True)
    chip.write_manifest(f'inputs/{chip.get("design")}.pkg.json')

    _select_inputs(chip, step, index)
    _copy_previous_steps_output_data(chip, step, index, replay)

    # Check manifest
    if not chip.get('option', 'skipcheck'):
        if not chip.check_manifest():
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
    workdir = chip._getworkdir(step=step, index=index)

    if os.path.isdir(workdir) and not replay:
        shutil.rmtree(workdir)
    os.makedirs(workdir, exist_ok=True)
    os.makedirs(os.path.join(workdir, 'inputs'), exist_ok=True)
    os.makedirs(os.path.join(workdir, 'outputs'), exist_ok=True)
    os.makedirs(os.path.join(workdir, 'reports'), exist_ok=True)
    return workdir


def _merge_input_dependencies_manifests(chip, step, index, status, replay):
    '''
    Merge manifests from all input dependencies
    '''

    design = chip.get('design')
    flow = chip.get('option', 'flow')
    in_job = chip._get_in_job(step, index)

    if not chip.get('option', 'remote') and not replay:
        for in_step, in_index in _get_flowgraph_node_inputs(chip, flow, (step, index)):
            if (in_step, in_index) in status:
                in_node_status = status[(in_step, in_index)]
                chip.set('flowgraph', flow, in_step, in_index, 'status', in_node_status)
            in_workdir = chip._getworkdir(in_job, in_step, in_index)
            cfgfile = f"{in_workdir}/outputs/{design}.pkg.json"
            if os.path.isfile(cfgfile):
                chip._read_manifest(cfgfile, clobber=False, partial=True)


def _select_inputs(chip, step, index):

    flow = chip.get('option', 'flow')
    tool, _ = chip._get_tool_task(step, index, flow)
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

    chip.set('flowgraph', flow, step, index, 'select', sel_inputs)


def _copy_previous_steps_output_data(chip, step, index, replay):
    '''
    Copy (link) output data from previous steps
    '''

    design = chip.get('design')
    flow = chip.get('option', 'flow')
    in_job = chip._get_in_job(step, index)
    if not _get_pruned_node_inputs(chip, flow, (step, index)):
        all_inputs = []
    elif not chip.get('flowgraph', flow, step, index, 'select'):
        all_inputs = _get_pruned_node_inputs(chip, flow, (step, index))
    else:
        all_inputs = chip.get('flowgraph', flow, step, index, 'select')

    strict = chip.get('option', 'strict')
    tool, task = chip._get_tool_task(step, index)
    in_files = chip.get('tool', tool, 'task', task, 'input', step=step, index=index)
    for in_step, in_index in all_inputs:
        if chip.get('flowgraph', flow, in_step, in_index, 'status') == NodeStatus.ERROR:
            chip.logger.error(f'Halting step due to previous error in {in_step}{in_index}')
            _haltstep(chip, flow, step, index)

        # Skip copying pkg.json files here, since we write the current chip
        # configuration into inputs/{design}.pkg.json earlier in _runstep.
        if not replay:
            in_workdir = chip._getworkdir(in_job, in_step, in_index)

            for outfile in os.scandir(f"{in_workdir}/outputs"):
                new_name = input_file_node_name(outfile.name, in_step, in_index)
                if strict:
                    if outfile.name not in in_files and new_name not in in_files:
                        continue

                if outfile.is_file() or outfile.is_symlink():
                    if outfile.name == f'{design}.pkg.json':
                        continue
                    utils.link_symlink_copy(outfile.path, f'inputs/{outfile.name}')
                elif outfile.is_dir():
                    shutil.copytree(outfile.path,
                                    f'inputs/{outfile.name}',
                                    dirs_exist_ok=True,
                                    copy_function=utils.link_symlink_copy)

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

    fullexe = chip._getexe(tool, step, index)

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
        work_dir = chip._getworkdir(step=step, index=index)
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
    tool, task = chip._get_tool_task(step, index, flow)

    quiet = (
        chip.get('option', 'quiet', step=step, index=index) and not
        chip.get('option', 'breakpoint', step=step, index=index)
    )

    # TODO: Currently no memory usage tracking in breakpoints, builtins, or unexpected errors.
    max_mem_bytes = 0

    retcode = 0
    cmdlist = []
    cmd_args = []
    if run_func and not chip.get('option', 'skipall'):
        logfile = None
        try:
            retcode = run_func(chip)
        except Exception as e:
            chip.logger.error(f'Failed in run() for {tool}/{task}: {e}')
            retcode = 1  # default to non-zero
            print_traceback(chip, e)
            chip._error = True
    elif not chip.get('option', 'skipall'):
        cmdlist, printable_cmd, _, cmd_args = _makecmd(chip, tool, task, step, index)

        ##################
        # Make record of tool options
        __record_tool(chip, step, index, version, toolpath, cmd_args)

        chip.logger.info('Running in %s', workdir)
        chip.logger.info('%s', printable_cmd)
        timeout = chip.get('flowgraph', flow, step, index, 'timeout')
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
                    kill_process(chip, proc, tool, 5 * POLL_INTERVAL)
                    chip._error = True

                # Read the remaining
                __read_std_streams(chip,
                                   quiet,
                                   is_stdout_log, stdout_reader,
                                   is_stderr_log, stderr_reader)
                retcode = proc.returncode

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
    chip._record_metric(step, index, 'memory', max_mem_bytes, source=None, source_unit='B')


def _post_process(chip, step, index):
    flow = chip.get('option', 'flow')
    tool, task = chip._get_tool_task(step, index, flow)
    if not chip.get('option', 'skipall'):
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
    if (not chip.get('option', 'skipall')) and (run_func is None):
        log_file = os.path.join(chip._getworkdir(step=step, index=index), f'{step}.log')
        matches = chip.check_logfile(step=step, index=index,
                                     display=not quiet,
                                     logfile=log_file)
        if 'errors' in matches:
            errors = chip.get('metric', 'errors', step=step, index=index)
            if errors is None:
                errors = 0
            errors += matches['errors']
            chip._record_metric(step, index, 'errors', errors, f'{step}.log')
        if 'warnings' in matches:
            warnings = chip.get('metric', 'warnings', step=step, index=index)
            if warnings is None:
                warnings = 0
            warnings += matches['warnings']
            chip._record_metric(step, index, 'warnings', warnings, f'{step}.log')


def _executenode(chip, step, index, replay):
    workdir = chip._getworkdir(step=step, index=index)
    flow = chip.get('option', 'flow')
    tool, _ = chip._get_tool_task(step, index, flow)

    _pre_process(chip, step, index)
    _set_env_vars(chip, step, index)

    run_func = getattr(chip._get_task_module(step, index, flow=flow), 'run', None)
    (toolpath, version) = _check_tool_version(chip, step, index, run_func)

    # Write manifest (tool interface) (Don't move this!)
    _write_task_manifest(chip, tool)

    # Start CPU Timer
    chip.logger.debug("Starting executable")
    cpu_start = time.time()

    _run_executable_or_builtin(chip, step, index, version, toolpath, workdir, run_func)

    # Capture cpu runtime
    cpu_end = time.time()
    cputime = round((cpu_end - cpu_start), 2)
    chip._record_metric(step, index, 'exetime', cputime, source=None, source_unit='s')

    _post_process(chip, step, index)

    _finalizenode(chip, step, index, replay)


def _pre_process(chip, step, index):
    flow = chip.get('option', 'flow')
    tool, task = chip._get_tool_task(step, index, flow)
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
    tool, task = chip._get_tool_task(step, index, flow)
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
    tool, task = chip._get_tool_task(step, index, flow)

    vercheck = not chip.get('option', 'novercheck', step=step, index=index)
    veropt = chip.get('tool', tool, 'vswitch')
    exe = chip._getexe(tool, step, index)
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
                    chip.logger.error(f"Tool '{exe_base}' responsed with: {proc.stdout}")
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
    tool, task = chip._get_tool_task(step, index, flow)
    if chip.get('option', 'hash'):
        if not setup:
            # hash all outputs
            chip.hash_files('tool', tool, 'task', task, 'output',
                            step=step, index=index, check=False)
        else:
            for task_key in ('refdir', 'prescript', 'postscript', 'script'):
                chip.hash_files('tool', tool, 'task', task, task_key,
                                step=step, index=index, check=False, allow_cache=True)

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
                    chip.hash_files(*args, check=False, allow_cache=True)
                else:
                    if not setup:
                        if chip.get(*args, field='filehash', step=step, index=index):
                            continue
                    chip.hash_files(*args, step=step, index=index, check=False, allow_cache=True)


def _finalizenode(chip, step, index, replay):
    flow = chip.get('option', 'flow')
    tool, task = chip._get_tool_task(step, index, flow)
    quiet = (
        chip.get('option', 'quiet', step=step, index=index) and not
        chip.get('option', 'breakpoint', step=step, index=index)
    )
    run_func = getattr(chip._get_task_module(step, index, flow=flow), 'run', None)

    _check_logfile(chip, step, index, quiet, run_func)
    _hash_files(chip, step, index)

    # Capture wall runtime and cpu cores
    wall_end = time.time()
    __record_time(chip, step, index, wall_end, 'end')

    walltime = wall_end - get_record_time(chip, step, index, 'starttime')
    chip._record_metric(step, index, 'tasktime', walltime, source=None, source_unit='s')
    chip.logger.info(f"Finished task in {round(walltime, 2)}s")

    # Save a successful manifest
    chip.set('flowgraph', flow, step, index, 'status', NodeStatus.SUCCESS)
    chip.write_manifest(os.path.join("outputs", f"{chip.get('design')}.pkg.json"))

    if chip._error and not replay:
        _make_testcase(chip, step, index)

    # Stop if there are errors
    errors = chip.get('metric', 'errors', step=step, index=index)
    if errors and not chip.get('option', 'flowcontinue', step=step, index=index):
        # TODO: should we warn if errors is not set?
        chip.logger.error(f'{tool} reported {errors} errors during {step}{index}')
        _haltstep(chip, flow, step, index)

    if chip._error:
        _haltstep(chip, flow, step, index)

    # Clean up non-essential files
    if chip.get('option', 'clean'):
        _eda_clean(chip, tool, task, step, index)

    if chip.get('option', 'strict') and not chip.get('option', 'skipall'):
        assert_output_files(chip, step, index)


def _make_testcase(chip, step, index):
    # Import here to avoid circular import
    from siliconcompiler.issue import generate_testcase

    generate_testcase(
        chip,
        step,
        index,
        archive_directory=chip._getworkdir(),
        include_pdks=False,
        include_specific_pdks=lambdapdk.get_pdks(),
        include_libraries=False,
        include_specific_libraries=lambdapdk.get_libs(),
        hash_files=chip.get('option', 'hash'),
        verbose_collect=False)


def assert_output_files(chip, step, index):
    flow = chip.get('option', 'flow')
    tool, task = chip._get_tool_task(step, index, flow)

    if chip._is_builtin(tool, task):
        return

    outputs = os.listdir(f'{chip._getworkdir(step=step, index=index)}/outputs')
    outputs.remove(f'{chip.design}.pkg.json')

    output_files = chip.get('tool', tool, 'task', task, 'output',
                            step=step, index=index)

    if set(outputs) != set(output_files):
        chip.error(f'Output files set {output_files} for {step}{index} does not match generated '
                   f'outputs: {outputs}',
                   fatal=True)


###########################################################################
def _eda_clean(chip, tool, task, step, index):
    '''Cleans up work directory of unnecessary files.

    Assumes our cwd is the workdir for step and index.
    '''

    keep = ['inputs', 'outputs', 'reports', f'{step}.log', f'sc_{step}{index}.log', 'replay.sh']

    manifest_format = chip.get('tool', tool, 'format')
    if manifest_format:
        keep.append(f'sc_manifest.{manifest_format}')

    for suffix in chip.getkeys('tool', tool, 'task', task, 'regex'):
        if chip.get('tool', tool, 'task', task, 'regex', suffix, step=step, index=index):
            keep.append(f'{step}.{suffix}')

    # Tool-specific keep files
    keep.extend(chip.get('tool', tool, 'task', task, 'keep', step=step, index=index))

    for path in os.listdir():
        if path in keep:
            continue
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)


def _reset_flow_nodes(chip, flow, nodes_to_execute):
    # Reset flowgraph/records/metrics by probing build directory. We need
    # to set values to None for steps we may re-run so that merging
    # manifests from _runtask() actually updates values.

    def clear_node(step, index):
        chip.set('flowgraph', flow, step, index, 'status', None)

        # Reset metrics and records
        for metric in chip.getkeys('metric'):
            chip._clear_metric(step, index, metric)
        for record in chip.getkeys('record'):
            chip._clear_record(step, index, record, preserve=['remoteid'])

    should_resume = chip.get("option", 'resume')
    for step, index in _get_flowgraph_nodes(chip, flow):
        stepdir = chip._getworkdir(step=step, index=index)
        cfg = f"{stepdir}/outputs/{chip.get('design')}.pkg.json"

        if not os.path.isdir(stepdir) or (
                (step, index) in nodes_to_execute and not should_resume):
            # If stepdir doesn't exist, we need to re-run this task. If
            # we're not running with -resume, we also re-run anything
            # in the nodes to execute.
            clear_node(step, index)
        elif os.path.isfile(cfg):
            node_status = Schema(manifest=cfg).get('flowgraph', flow, step, index, 'status')
            chip.set('flowgraph', flow, step, index, 'status', node_status)
        else:
            chip.set('flowgraph', flow, step, index, 'status', NodeStatus.ERROR)

    for step in chip.getkeys('flowgraph', flow):
        all_indices_failed = True
        for index in chip.getkeys('flowgraph', flow, step):
            if chip.get('flowgraph', flow, step, index, 'status') == NodeStatus.SUCCESS:
                all_indices_failed = False

        if should_resume and all_indices_failed:
            # When running with -resume, we re-run any step in flowgraph that
            # had all indices fail.
            for index in chip.getkeys('flowgraph', flow, step):
                if (step, index) in nodes_to_execute:
                    clear_node(step, index)


def _prepare_nodes(chip, nodes_to_run, processes, local_processes, flow, status):
    '''
    For each node to run, prepare a process and store its dependencies
    '''
    # Ensure we use spawn for multiprocessing so loggers initialized correctly
    jobname = chip.get('option', 'jobname')
    multiprocessor = multiprocessing.get_context('spawn')
    collected = False
    for (step, index) in chip.nodes_to_execute(flow):
        node = (step, index)

        if status[node] != NodeStatus.PENDING:
            continue

        if (chip._get_in_job(step, index) != jobname):
            # If we specify a different job as input to this task,
            # we assume we are good to run it.
            nodes_to_run[node] = []
        else:
            nodes_to_run[node] = _get_pruned_node_inputs(chip, flow, (step, index))

        exec_func = _executenode

        if chip.get('option', 'scheduler', 'name', step=step, index=index):
            # Defer job to compute node
            # If the job is configured to run on a cluster, collect the schema
            # and send it to a compute node for deferred execution.
            if not _get_flowgraph_node_inputs(chip, chip.get('option', 'flow'), (step, index)):
                if not collected:
                    chip._collect()
                    collected = True
            exec_func = slurm._defernode
        else:
            local_processes.append((step, index))

        processes[node] = multiprocessor.Process(target=_runtask,
                                                 args=(chip, flow, step, index, status, exec_func))


def _check_node_dependencies(chip, node, deps, status, deps_was_successful):
    had_deps = len(deps) > 0
    step, index = node
    tool, task = chip._get_tool_task(step, index)

    # Clear any nodes that have finished from dependency list.
    for in_node in deps.copy():
        if status[in_node] != NodeStatus.PENDING:
            deps.remove(in_node)
        if status[in_node] == NodeStatus.SUCCESS:
            deps_was_successful[node] = True
        if status[in_node] == NodeStatus.ERROR:
            # Fail if any dependency failed for non-builtin task
            if not chip._is_builtin(tool, task):
                deps.clear()
                status[node] = NodeStatus.ERROR
                return

    # Fail if no dependency successfully finished for builtin task
    if had_deps and len(deps) == 0 \
            and chip._is_builtin(tool, task) and not deps_was_successful.get(node):
        status[node] = NodeStatus.ERROR


def _launch_nodes(chip, nodes_to_run, processes, local_processes, status):
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
        tool, task = chip._get_tool_task(step, index)
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

    while len(nodes_to_run) > 0 or len(running_nodes) > 0:
        # Check for new nodes that can be launched.
        for node, deps in list(nodes_to_run.items()):
            # TODO: breakpoint logic:
            # if node is breakpoint, then don't launch while len(running_nodes) > 0

            _check_node_dependencies(chip, node, deps, status, deps_was_successful)

            if status[node] == NodeStatus.ERROR:
                del nodes_to_run[node]
                continue

            # If there are no dependencies left, launch this node and
            # remove from nodes_to_run.
            if len(deps) == 0:
                dostart, requested_threads = allow_start(node)

                if dostart:
                    processes[node].start()
                    del nodes_to_run[node]
                    running_nodes[node] = requested_threads

        # Check for situation where we have stuff left to run but don't
        # have any nodes running. This shouldn't happen, but we will get
        # stuck in an infinite loop if it does, so we want to break out
        # with an explicit error.
        if len(nodes_to_run) > 0 and len(running_nodes) == 0:
            chip.error('Nodes left to run, but no '
                       'running nodes. From/to may be invalid.', fatal=True)

        # Check for completed nodes.
        # TODO: consider staying in this section of loop until a node
        # actually completes.
        for node in list(running_nodes.keys()):
            if not processes[node].is_alive():
                del running_nodes[node]
                if processes[node].exitcode > 0:
                    status[node] = NodeStatus.ERROR
                else:
                    status[node] = NodeStatus.SUCCESS

        # TODO: exponential back-off with max?
        time.sleep(0.1)


def _check_nodes_status(chip, flow, status):
    def success(node):
        return status[node] == NodeStatus.SUCCESS
    unreachable_steps = _unreachable_steps_to_execute(chip, flow, cond=success)
    if unreachable_steps:
        chip.error(f'These final steps could not be reached: {list(unreachable_steps)}', fatal=True)

    # On success, write out status dict to flowgraph status. We do this
    # since certain scenarios won't be caught by reading in manifests (a
    # failing step doesn't dump a manifest). For example, if the
    # final steps have two indices and one fails.
    for (step, index) in chip.nodes_to_execute(flow):
        node = (step, index)
        if status[node] != NodeStatus.PENDING:
            chip.set('flowgraph', flow, step, index, 'status', status[node])


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
    trace = StringIO()
    traceback.print_tb(exception.__traceback__, file=trace)
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

    if not chip.get('option', 'resume'):
        return True

    # Load previous manifest
    input_manifest = None
    in_cfg = f"{chip._getworkdir(step=step, index=index)}/inputs/{chip.design}.pkg.json"
    if os.path.exists(in_cfg):
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

    tool, task = chip._get_tool_task(step, index)
    input_tool, input_task = input_chip._get_tool_task(step, index)

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

    def print_warning(key):
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
