import contextlib
import logging
import os
import psutil
import re
import shlex
import shutil
import subprocess
import sys
import time

try:
    import resource
except ModuleNotFoundError:
    resource = None

try:
    # Note: this import throws exception on Windows
    import pty
except ModuleNotFoundError:
    pty = None

import os.path

from packaging.version import Version, InvalidVersion
from packaging.specifiers import SpecifierSet, InvalidSpecifier

from siliconcompiler.schema import NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter, PerNode, Scope
from siliconcompiler.schema.utils import trim

from siliconcompiler import utils
from siliconcompiler import sc_open

from siliconcompiler.record import RecordTool
from siliconcompiler.flowgraph import RuntimeFlowgraph


class TaskError(Exception):
    '''
    Error indicates execution cannot continue and should be terminated
    '''


class TaskTimeout(TaskError):
    '''
    Error indicates a timeout has occurred

    Args:
        timeout (float): execution time at timeout
    '''
    def __init__(self, *args, timeout=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = timeout


class TaskExecutableNotFound(TaskError):
    '''
    Executable not found.
    '''


class TaskSchema(NamedSchema):
    def __init__(self, name=None):
        super().__init__(name=name)

        schema_task(self)


class ToolSchema(NamedSchema):
    __parse_version_check_str = r"""
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
    __parse_version_check = re.compile(
        r"^\s*" + __parse_version_check_str + r"\s*$",
        re.VERBOSE | re.IGNORECASE)

    def __init__(self, name=None):
        super().__init__(name=name)

        schema_tool(self)

        schema = EditableSchema(self)
        schema.insert("task", "default", TaskSchema())

        self.set_runtime(None)

    def set_runtime(self, chip, step=None, index=None):
        '''
        Sets the runtime information needed to properly execute a task.
        Note: unstable API

        Args:
            chip (:class:`Chip`): root schema for the runtime information
        '''
        self.__chip = None
        self.__schema_full = None
        self.__logger = None
        if chip:
            self.__chip = chip
            self.__schema_full = chip.schema
            self.__logger = chip.logger

        self.__step = step
        self.__index = index
        self.__tool = None
        self.__task = None

        self.__schema_record = None
        self.__schema_metric = None
        self.__schema_flow = None
        if self.__schema_full:
            self.__schema_record = self.__schema_full.get("record", field="schema")
            self.__schema_metric = self.__schema_full.get("metric", field="schema")

            if not self.__step:
                self.__step = self.__schema_full.get('arg', 'step')
            if not self.__index:
                self.__index = self.__schema_full.get('arg', 'index')

            if not self.__step or not self.__index:
                raise RuntimeError("step or index not specified")

            flow = self.__schema_full.get('option', 'flow')
            if not flow:
                raise RuntimeError("flow not specified")
            self.__schema_flow = self.__schema_full.get("flowgraph", flow, field="schema")
            self.__tool = self.__schema_flow.get(self.__step, self.__index, 'tool')
            self.__task = self.__schema_flow.get(self.__step, self.__index, 'task')

    def node(self):
        '''
        Returns:
            step and index for the current runtime
        '''

        return self.__step, self.__index

    def tool(self):
        '''
        Returns:
            task name
        '''

        return self.__tool

    def task(self):
        '''
        Returns:
            task name
        '''

        return self.__task

    def logger(self):
        '''
        Returns:
            logger
        '''
        return self.__logger

    def schema(self, type=None):
        '''
        Get useful section of the schema.

        Args:
            type (str): schema section to find, if None returns the root schema.

        Returns:
            schema section.
        '''
        if type is None:
            return self.__schema_full
        elif type == "record":
            return self.__schema_record
        elif type == "metric":
            return self.__schema_metric
        elif type == "flow":
            return self.__schema_flow
        else:
            raise ValueError(f"{type} is not a schema section")

    def get_exe(self):
        '''
        Determines the absolute path for the specified executable.

        Raises:
            :class:`TaskExecutableNotFound`: if executable not found.

        Returns:
            path to executable, or None if not specified
        '''

        exe = self.get('exe')

        if exe is None:
            return None

        # Collect path
        env = self.get_runtime_environmental_variables(include_path=True)

        fullexe = shutil.which(exe, path=env["PATH"])

        if not fullexe:
            raise TaskExecutableNotFound(f"{exe} could not be found")

        return fullexe

    def get_exe_version(self):
        '''
        Gets the version of the specified executable.

        Raises:
            :class:`TaskExecutableNotFound`: if executable not found.
            :class:`NotImplementedError`: if :meth:`.parse_version` has not be implemented.

        Returns:
            version determined by :meth:`.parse_version`.
        '''

        veropt = self.get('vswitch')
        if not veropt:
            return None

        exe = self.get_exe()
        if not exe:
            return None

        exe_path, exe_base = os.path.split(exe)

        cmdlist = [exe]
        cmdlist.extend(veropt)

        self.__logger.debug(f'Running {self.name()} version check: {" ".join(cmdlist)}')

        proc = subprocess.run(cmdlist,
                              stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              universal_newlines=True)

        if proc.returncode != 0:
            self.__logger.warning(f"Version check on '{exe_base}' ended with "
                                  f"code {proc.returncode}")

        try:
            version = self.parse_version(proc.stdout)
        except NotImplementedError:
            raise NotImplementedError(f'{self.name()} does not implement parse_version()')
        except Exception as e:
            self.__logger.error(f'{self.name()} failed to parse version string: {proc.stdout}')
            raise e from None

        self.__logger.info(f"Tool '{exe_base}' found with version '{version}' "
                           f"in directory '{exe_path}'")

        return version

    def check_exe_version(self, reported_version):
        '''
        Check if the reported version matches the versions specified in
        :keypath:`tool,<tool>,version`.

        Args:
            reported_version (str): version to check

        Returns:
            True if the version matched, false otherwise

        '''

        spec_sets = self.get('version', step=self.__step, index=self.__index)
        if not spec_sets:
            # No requirement so always true
            return True

        for spec_set in spec_sets:
            split_specs = [s.strip() for s in spec_set.split(",") if s.strip()]
            specs_list = []
            for spec in split_specs:
                match = re.match(ToolSchema.__parse_version_check, spec)
                if match is None:
                    self.__logger.warning(f'Invalid version specifier {spec}. '
                                          f'Defaulting to =={spec}.')
                    operator = '=='
                    spec_version = spec
                else:
                    operator = match.group('operator')
                    spec_version = match.group('version')
                specs_list.append((operator, spec_version))

            try:
                normalized_version = self.normalize_version(reported_version)
            except Exception as e:
                self.__logger.error(f'Unable to normalize version for {self.name()}: '
                                    f'{reported_version}')
                raise e from None

            try:
                version = Version(normalized_version)
            except InvalidVersion:
                self.__logger.error(f'Version {normalized_version} reported by {self.name()} does '
                                    'not match standard.')
                return False

            try:
                normalized_spec_list = [
                    f'{op}{self.normalize_version(ver)}' for op, ver in specs_list]
                normalized_specs = ','.join(normalized_spec_list)
            except Exception as e:
                self.__logger.error(f'Unable to normalize versions for {self.name()}: '
                                    f'{",".join([f"{op}{ver}" for op, ver in specs_list])}')
                raise e from None

            try:
                spec_set = SpecifierSet(normalized_specs)
            except InvalidSpecifier:
                self.__logger.error(f'Version specifier set {normalized_specs} '
                                    'does not match standard.')
                return False

            if version in spec_set:
                return True

        allowedstr = '; '.join(spec_sets)
        self.__logger.error(f"Version check failed for {self.name()}. Check installation.")
        self.__logger.error(f"Found version {reported_version}, "
                            f"did not satisfy any version specifier set {allowedstr}.")
        return False

    def get_runtime_environmental_variables(self, include_path=True):
        '''
        Determine the environmental variables needed for the task

        Args:
            include_path (bool): if True, includes PATH variable

        Returns:
            dict of str: dictionary of environmental variable to value mapping
        '''

        # Add global environmental vars
        envvars = {}
        for env in self.__schema_full.getkeys('option', 'env'):
            envvars[env] = self.__schema_full.get('option', 'env', env)

        # Add tool specific vars
        for lic_env in self.getkeys('licenseserver'):
            license_file = self.get('licenseserver', lic_env, step=self.__step, index=self.__index)
            if license_file:
                envvars[lic_env] = ':'.join(license_file)

        if include_path:
            path_param = self.get('path', field=None, step=self.__step, index=self.__index)
            if path_param.get(field='package'):
                raise NotImplementedError

            envvars["PATH"] = os.getenv("PATH", os.defpath)

            path = path_param.get(field=None).resolve_path()  # TODO: needs package search
            if path:
                envvars["PATH"] = path + os.pathsep + envvars["PATH"]

            # Forward additional variables
            for var in ('LD_LIBRARY_PATH',):
                val = os.getenv(var, None)
                if val:
                    envvars[var] = val

        # Add task specific vars
        for env in self.getkeys('task', self.__task, 'env'):
            envvars[env] = self.get('task', self.__task, 'env', env,
                                    step=self.__step, index=self.__index)

        return envvars

    def get_runtime_arguments(self):
        '''
        Constructs the arguments needed to run the task.

        Returns:
            command (list)
        '''

        cmdargs = []
        cmdargs.extend(self.get('task', self.__task, 'option',
                                step=self.__step, index=self.__index))

        # Add scripts files / TODO:
        scripts = self.__chip.find_files('tool', self.__tool, 'task', self.__task, 'script',
                                         step=self.__step, index=self.__index)

        cmdargs.extend(scripts)

        try:
            cmdargs.extend(self.runtime_options())
        except Exception as e:
            self.__logger.error(f'Failed to get runtime options for {self.name()}/{self.__task}')
            raise e from None

        # Cleanup args
        cmdargs = [str(arg).strip() for arg in cmdargs]

        return cmdargs

    def generate_replay_script(self, filepath, workdir, include_path=True):
        '''
        Generate a replay script for the task.

        Args:
            filepath (path): path to the file to write
            workdir (path): path to the run work directory
            include_path (bool): include path information in environmental variables
        '''
        replay_opts = {}
        replay_opts["work_dir"] = workdir
        replay_opts["exports"] = self.get_runtime_environmental_variables(include_path=include_path)

        replay_opts["executable"] = self.get('exe')
        replay_opts["step"] = self.__step
        replay_opts["index"] = self.__index
        replay_opts["cfg_file"] = f"inputs/{self.__chip.design}.pkg.json"
        replay_opts["node_only"] = 0 if replay_opts["executable"] else 1

        vswitch = self.get('vswitch')
        if vswitch:
            replay_opts["version_flag"] = shlex.join(vswitch)

        # detect arguments
        arg_test = re.compile(r'^[-+]')

        # detect file paths
        file_test = re.compile(r'^[/\.]')

        if replay_opts["executable"]:
            format_cmd = [replay_opts["executable"]]

            for cmdarg in self.get_runtime_arguments():
                add_new_line = len(format_cmd) == 1

                if arg_test.match(cmdarg) or file_test.match(cmdarg):
                    add_new_line = True
                else:
                    if not arg_test.match(format_cmd[-1]):
                        add_new_line = True

                cmdarg = shlex.quote(cmdarg)
                if add_new_line:
                    format_cmd.append(cmdarg)
                else:
                    format_cmd[-1] += f' {cmdarg}'
        else:
            format_cmd = []
        replay_opts["cmds"] = format_cmd

        # create replay file
        with open(filepath, 'w') as f:
            f.write(utils.get_file_template("replay/replay.sh.j2").render(replay_opts))
            f.write("\n")

        os.chmod(filepath, 0o755)

    def setup_work_directory(self, workdir, remove_exist=True):
        '''
        Create the runtime directories needed to execute a task.

        Args:
            workdir (path): path to the run work directory
            remove_exist (bool): if True, removes the existing directory
        '''

        # Delete existing directory
        if os.path.isdir(workdir) and remove_exist:
            shutil.rmtree(workdir)

        # Create directories
        os.makedirs(workdir, exist_ok=True)
        os.makedirs(os.path.join(workdir, 'inputs'), exist_ok=True)
        os.makedirs(os.path.join(workdir, 'outputs'), exist_ok=True)
        os.makedirs(os.path.join(workdir, 'reports'), exist_ok=True)

    def write_task_manifest(self, directory, backup=True):
        '''
        Write the manifest needed for the task

        Args:
            directory (path): directory to write the manifest into.
            backup (bool): if True and an existing manifest is found a backup is kept.
        '''

        suffix = self.get('format')
        if not suffix:
            return

        manifest_path = os.path.join(directory, f"sc_manifest.{suffix}")

        if backup and os.path.exists(manifest_path):
            shutil.copyfile(manifest_path, f'{manifest_path}.bak')

        # TODO: pull in TCL/yaml here
        self.__chip.write_manifest(manifest_path, abspath=True)

    def __get_io_file(self, io_type):
        '''
        Get the runtime destination for the io type.

        Args:
            io_type (str): name of io type
        '''
        suffix = self.get('task', self.__task, io_type, 'suffix',
                          step=self.__step, index=self.__index)
        destination = self.get('task', self.__task, io_type, 'destination',
                               step=self.__step, index=self.__index)

        io_file = None
        io_log = False
        if destination == 'log':
            io_file = f"{self.__step}.{suffix}"
            io_log = True
        elif destination == 'output':
            io_file = os.path.join('outputs', f"{self.__chip.top()}.{suffix}")
        elif destination == 'none':
            io_file = os.devnull

        return io_file, io_log

    def __terminate_exe(self, proc):
        '''
        Terminates a subprocess

        Args:
            proc (subprocess.Process): process to terminate
        '''

        def terminate_process(pid, timeout=3):
            '''Terminates a process and all its (grand+)children.

            Based on https://psutil.readthedocs.io/en/latest/#psutil.wait_procs and
            https://psutil.readthedocs.io/en/latest/#kill-process-tree.
            '''
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            children.append(parent)
            for p in children:
                try:
                    p.terminate()
                except psutil.NoSuchProcess:
                    # Process may have terminated on its own in the meantime
                    pass

            _, alive = psutil.wait_procs(children, timeout=timeout)
            for p in alive:
                # If processes are still alive after timeout seconds, send more
                # aggressive signal.
                p.kill()

        TERMINATE_TIMEOUT = 5

        terminate_process(proc.pid, timeout=TERMINATE_TIMEOUT)
        self.__logger.info(f'Waiting for {self.name()} to exit...')
        try:
            proc.wait(timeout=TERMINATE_TIMEOUT)
        except subprocess.TimeoutExpired:
            if proc.poll() is None:
                self.__logger.warning(f'{self.name()} did not exit within {TERMINATE_TIMEOUT} '
                                      'seconds. Terminating...')
                terminate_process(proc.pid, timeout=TERMINATE_TIMEOUT)

    def run_task(self, workdir, quiet, loglevel, breakpoint, nice, timeout):
        '''
        Run the task.

        Raises:
            :class:`TaskError`: raised if the task failed to complete and
                should not be considered complete.
            :class:`TaskTimeout`: raised if the task reaches a timeout

        Args:
            workdir (path): path to the run work directory
            quiet (bool): if True, execution output is suppressed
            loglevel (str): logging level
            breakpoint (bool): if True, will attempt to execute with a breakpoint
            nice (int): POSIX nice level to use in execution
            timeout (int): timeout to use for execution

        Returns:
            return code from the execution
        '''

        # TODO: Currently no memory usage tracking in breakpoints, builtins, or unexpected errors.
        max_mem_bytes = 0
        cpu_start = time.time()

        # Ensure directories are setup
        self.setup_work_directory(workdir, remove_exist=False)

        # Write task manifest
        self.write_task_manifest(workdir)

        # Get file IO
        stdout_file, is_stdout_log = self.__get_io_file("stdout")
        stderr_file, is_stderr_log = self.__get_io_file("stderr")

        stdout_print = self.__logger.info
        stderr_print = self.__logger.error
        if loglevel == "quiet":
            stdout_print = self.__logger.error
            stderr_print = self.__logger.error

        def read_stdio(stdout_reader, stderr_reader):
            if quiet:
                return

            if is_stdout_log and stdout_reader:
                for line in stdout_reader.readlines():
                    stdout_print(line.rstrip())
            if is_stderr_log and stderr_reader:
                for line in stderr_reader.readlines():
                    stderr_print(line.rstrip())

        exe = self.get_exe()

        retcode = 0
        if not exe:
            # No executable, so must call run()
            try:
                with open(stdout_file, 'w') as stdout_writer, \
                        open(stderr_file, 'w') as stderr_writer:
                    if stderr_file == stdout_file:
                        stderr_writer.close()
                        stderr_writer = sys.stdout

                    with contextlib.redirect_stderr(stderr_writer), \
                            contextlib.redirect_stdout(stdout_writer):
                        retcode = self.run()
            except Exception as e:
                self.__logger.error(f'Failed in run() for {self.name()}/{self.__task}: {e}')
                utils.print_traceback(self.__logger, e)
                raise e
            finally:
                with sc_open(stdout_file) as stdout_reader, \
                        sc_open(stderr_file) as stderr_reader:
                    read_stdio(stdout_reader, stderr_reader)

                if resource:
                    try:
                        # Since memory collection is not possible, collect the current process
                        # peak memory
                        max_mem_bytes = max(
                            max_mem_bytes,
                            1024 * resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                    except (OSError, ValueError, PermissionError):
                        pass
        else:
            cmdlist = self.get_runtime_arguments()

            # Make record of tool options
            self.schema("record").record_tool(
                self.__step, self.__index,
                cmdlist, RecordTool.ARGS)

            self.__logger.info(shlex.join([os.path.basename(exe), *cmdlist]))

            if not pty and breakpoint:
                # pty not available
                breakpoint = False

            if breakpoint and sys.platform in ('darwin', 'linux'):
                # When we break on a step, the tool often drops into a shell.
                # However, our usual subprocess scheme seems to break terminal
                # echo for some tools. On POSIX-compatible systems, we can use
                # pty to connect the tool to our terminal instead. This code
                # doesn't handle quiet/timeout logic, since we don't want either
                # of these features for an interactive session. Logic for
                # forwarding to file based on
                # https://docs.python.org/3/library/pty.html#example.
                with open(f"{self.__step}.log", 'wb') as log_writer:
                    def read(fd):
                        data = os.read(fd, 1024)
                        log_writer.write(data)
                        return data
                    retcode = pty.spawn([exe, *cmdlist], read)
            else:
                with open(stdout_file, 'w') as stdout_writer, \
                        open(stdout_file, 'r', errors='replace_with_warning') as stdout_reader, \
                        open(stderr_file, 'w') as stderr_writer, \
                        open(stderr_file, 'r', errors='replace_with_warning') as stderr_reader:
                    # if STDOUT and STDERR are to be redirected to the same file,
                    # use a single writer
                    if stderr_file == stdout_file:
                        stderr_writer.close()
                        stderr_reader.close()
                        stderr_reader = None
                        stderr_writer = subprocess.STDOUT

                    preexec_fn = None
                    if nice is not None and hasattr(os, 'nice'):
                        def set_task_nice():
                            os.nice(nice)
                        preexec_fn = set_task_nice

                    try:
                        proc = subprocess.Popen([exe, *cmdlist],
                                                stdin=subprocess.DEVNULL,
                                                stdout=stdout_writer,
                                                stderr=stderr_writer,
                                                preexec_fn=preexec_fn)
                    except Exception as e:
                        raise TaskError(f"Unable to start {exe}: {str(e)}")

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
                                    self.__logger.warning(
                                        'Current system memory usage is '
                                        f'{memory_usage.percent:.1f}%')

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
                            read_stdio(stdout_reader, stderr_reader)

                            duration = time.time() - cpu_start
                            if timeout is not None and duration > timeout:
                                raise TaskTimeout(timeout=duration)

                            time.sleep(POLL_INTERVAL)
                    except KeyboardInterrupt:
                        self.__logger.info("Received ctrl-c.")
                        self.__terminate_exe(proc)
                        raise TaskError
                    except TaskTimeout as e:
                        self.__logger.error(f'Task timed out after {e.timeout:.1f} seconds')
                        self.__terminate_exe(proc)
                        raise e from None

                    # Read the remaining io
                    read_stdio(stdout_reader, stderr_reader)

                    retcode = proc.returncode

        # Record record information
        self.schema("record").record_tool(
            self.__step, self.__index,
            retcode, RecordTool.EXITCODE)

        # Capture runtime metrics
        self.schema("metric").record(
            self.__step, self.__index,
            'exetime', time.time() - cpu_start, unit='s')
        self.schema("metric").record(
            self.__step, self.__index,
            'memory', max_mem_bytes, unit='B')

        return retcode

    def __getstate__(self):
        state = self.__dict__.copy()

        # Remove runtime information
        for key in list(state.keys()):
            if key.startswith("_ToolSchema__"):
                del state[key]

        return state

    def __setstate__(self, state):
        self.__dict__ = state

        # Reinit runtime information
        self.set_runtime(None)

    def get_output_files(self):
        return set(self.get("task", self.__task, "output", step=self.__step, index=self.__index))

    ###############################################################
    def parse_version(self, stdout):
        raise NotImplementedError("must be implemented by the implementation class")

    def normalize_version(self, version):
        return version

    def setup(self):
        pass

    def select_input_nodes(self):
        flow = self.schema("flow")
        runtime = RuntimeFlowgraph(
            flow,
            from_steps=set([step for step, _ in flow.get_entry_nodes()]),
            prune_nodes=self.__chip.get('option', 'prune'))

        return runtime.get_node_inputs(self.__step, self.__index, record=self.schema("record"))

    def pre_process(self):
        pass

    def runtime_options(self):
        return []

    def run(self):
        raise NotImplementedError("must be implemented by the implementation class")

    def post_process(self):
        pass


###########################################################################
# Migration helper
###########################################################################
class ToolSchemaTmp(ToolSchema):
    def __module_func(self, name, modules):
        for module in modules:
            method = getattr(module, name, None)
            if method:
                return method
        return None

    def __tool_task_modules(self):
        step, index = self.node()
        flow = self._ToolSchema__chip.get('option', 'flow')
        return \
            self._ToolSchema__chip._get_tool_module(step, index, flow=flow), \
            self._ToolSchema__chip._get_task_module(step, index, flow=flow)

    def get_output_files(self):
        _, task = self.__tool_task_modules()
        method = self.__module_func("_gather_outputs", [task])
        if method:
            return method(self._ToolSchema__chip, *self.node())
        return ToolSchema.get_output_files(self)

    def parse_version(self, stdout):
        tool, _ = self.__tool_task_modules()
        method = self.__module_func("parse_version", [tool])
        if method:
            return method(stdout)
        return ToolSchema.parse_version(self, stdout)

    def normalize_version(self, version):
        tool, _ = self.__tool_task_modules()
        method = self.__module_func("normalize_version", [tool])
        if method:
            return method(version)
        return ToolSchema.normalize_version(self, version)

    def setup(self):
        _, task = self.__tool_task_modules()
        method = self.__module_func("setup", [task])
        if method:
            prev_step, prev_index = self._ToolSchema__chip.get('arg', 'step'), \
                self._ToolSchema__chip.get('arg', 'index')
            step, index = self.node()
            self._ToolSchema__chip.set('arg', 'step', step)
            self._ToolSchema__chip.set('arg', 'index', index)
            ret = method(self._ToolSchema__chip)
            self._ToolSchema__chip.set('arg', 'step', prev_step)
            self._ToolSchema__chip.set('arg', 'index', prev_index)
            return ret
        return ToolSchema.setup(self)

    def select_input_nodes(self):
        _, task = self.__tool_task_modules()
        method = self.__module_func("_select_inputs", [task])
        if method:
            prev_step, prev_index = self._ToolSchema__chip.get('arg', 'step'), \
                self._ToolSchema__chip.get('arg', 'index')
            step, index = self.node()
            self._ToolSchema__chip.set('arg', 'step', step)
            self._ToolSchema__chip.set('arg', 'index', index)
            ret = method(self._ToolSchema__chip, *self.node())
            self._ToolSchema__chip.set('arg', 'step', prev_step)
            self._ToolSchema__chip.set('arg', 'index', prev_index)
            return ret
        return ToolSchema.select_input_nodes(self)

    def pre_process(self):
        _, task = self.__tool_task_modules()
        method = self.__module_func("pre_process", [task])
        if method:
            prev_step, prev_index = self._ToolSchema__chip.get('arg', 'step'), \
                self._ToolSchema__chip.get('arg', 'index')
            step, index = self.node()
            self._ToolSchema__chip.set('arg', 'step', step)
            self._ToolSchema__chip.set('arg', 'index', index)
            ret = method(self._ToolSchema__chip)
            self._ToolSchema__chip.set('arg', 'step', prev_step)
            self._ToolSchema__chip.set('arg', 'index', prev_index)
            return ret
        return ToolSchema.pre_process(self)

    def runtime_options(self):
        tool, task = self.__tool_task_modules()
        method = self.__module_func("runtime_options", [task, tool])
        if method:
            prev_step, prev_index = self._ToolSchema__chip.get('arg', 'step'), \
                self._ToolSchema__chip.get('arg', 'index')
            step, index = self.node()
            self._ToolSchema__chip.set('arg', 'step', step)
            self._ToolSchema__chip.set('arg', 'index', index)
            ret = method(self._ToolSchema__chip)
            self._ToolSchema__chip.set('arg', 'step', prev_step)
            self._ToolSchema__chip.set('arg', 'index', prev_index)
            return ret
        return ToolSchema.runtime_options(self)

    def run(self):
        _, task = self.__tool_task_modules()
        method = self.__module_func("run", [task])
        if method:
            # Handle logger stdout suppression if quiet
            step, index = self.node()
            stdout_handler_level = self._ToolSchema__chip.logger._console.level
            if self._ToolSchema__chip.get('option', 'quiet', step=step, index=index):
                self._ToolSchema__chip.logger._console.setLevel(logging.CRITICAL)

            prev_step, prev_index = self._ToolSchema__chip.get('arg', 'step'), \
                self._ToolSchema__chip.get('arg', 'index')
            step, index = self.node()
            self._ToolSchema__chip.set('arg', 'step', step)
            self._ToolSchema__chip.set('arg', 'index', index)
            retcode = method(self._ToolSchema__chip)
            self._ToolSchema__chip.set('arg', 'step', prev_step)
            self._ToolSchema__chip.set('arg', 'index', prev_index)

            self._ToolSchema__chip.logger._console.setLevel(stdout_handler_level)

            return retcode
        return ToolSchema.run(self)

    def post_process(self):
        _, task = self.__tool_task_modules()
        method = self.__module_func("post_process", [task])
        if method:
            prev_step, prev_index = self._ToolSchema__chip.get('arg', 'step'), \
                self._ToolSchema__chip.get('arg', 'index')
            step, index = self.node()
            self._ToolSchema__chip.set('arg', 'step', step)
            self._ToolSchema__chip.set('arg', 'index', index)
            ret = method(self._ToolSchema__chip)
            self._ToolSchema__chip.set('arg', 'step', prev_step)
            self._ToolSchema__chip.set('arg', 'index', prev_index)
            return ret
        return ToolSchema.post_process(self)


###########################################################################
# Tool Setup
###########################################################################
def schema_tool(schema):
    schema = EditableSchema(schema)

    schema.insert(
        'exe',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Tool: executable name",
            switch="-tool_exe 'tool <str>'",
            example=["cli: -tool_exe 'openroad openroad'",
                     "api: chip.set('tool', 'openroad', 'exe', 'openroad')"],
            help=trim("""Tool executable name.""")))

    schema.insert(
        'sbom', 'default',
        Parameter(
            '[file]',
            scope=Scope.GLOBAL,
            pernode=PerNode.OPTIONAL,
            shorthelp="Tool: software BOM",
            switch="-tool_sbom 'tool version <file>'",
            example=[
                "cli: -tool_sbom 'yosys 1.0.1 ys_sbom.json'",
                "api: chip.set('tool', 'yosys', 'sbom', '1.0', 'ys_sbom.json')"],
            help=trim("""
            Paths to software bill of material (SBOM) document file of the tool
            specified on a per version basis. The SBOM includes critical
            package information about the tool including the list of included
            components, licenses, and copyright. The SBOM file is generally
            provided as in a a standardized open data format such as SPDX.""")))

    schema.insert(
        'path',
        Parameter(
            'dir',
            scope=Scope.GLOBAL,
            pernode=PerNode.OPTIONAL,
            shorthelp="Tool: executable path",
            switch="-tool_path 'tool <dir>'",
            example=[
                "cli: -tool_path 'openroad /usr/local/bin'",
                "api: chip.set('tool', 'openroad', 'path', '/usr/local/bin')"],
            help=trim("""
            File system path to tool executable. The path is prepended to the
            system PATH environment variable for batch and interactive runs. The
            path parameter can be left blank if the :keypath:`tool,<tool>,exe` is already in the
            environment search path.""")))

    schema.insert(
        'vswitch',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="Tool: executable version switch",
            switch="-tool_vswitch 'tool <str>'",
            example=["cli: -tool_vswitch 'openroad -version'",
                     "api: chip.set('tool', 'openroad', 'vswitch', '-version')"],
            help=trim("""
            Command line switch to use with executable used to print out
            the version number. Common switches include ``-v``, ``-version``,
            ``--version``. Some tools may require extra flags to run in batch mode.""")))

    schema.insert(
        'vendor',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Tool: vendor",
            switch="-tool_vendor 'tool <str>'",
            example=["cli: -tool_vendor 'yosys yosys'",
                     "api: chip.set('tool', 'yosys', 'vendor', 'yosys')"],
            help=trim("""
            Name of the tool vendor. Parameter can be used to set vendor
            specific technology variables in the PDK and libraries. For
            open source projects, the project name should be used in
            place of vendor.""")))

    schema.insert(
        'version',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            pernode=PerNode.OPTIONAL,
            shorthelp="Tool: version",
            switch="-tool_version 'tool <str>'",
            example=["cli: -tool_version 'openroad >=v2.0'",
                     "api: chip.set('tool', 'openroad', 'version', '>=v2.0')"],
            help=trim("""
            List of acceptable versions of the tool executable to be used. Each
            entry in this list must be a version specifier as described by Python
            `PEP-440 <https://peps.python.org/pep-0440/#version-specifiers>`_.
            During task execution, the tool is called with the 'vswitch' to
            check the runtime executable version. If the version of the system
            executable is not allowed by any of the specifiers in 'version',
            then the job is halted pre-execution. For backwards compatibility,
            entries that do not conform to the standard will be interpreted as a
            version with an '==' specifier. This check can be disabled by
            setting :keypath:`option,novercheck` to True.""")))

    schema.insert(
        'format',
        Parameter(
            '<json,tcl,yaml>',
            scope=Scope.GLOBAL,
            shorthelp="Tool: file format",
            switch="-tool_format 'tool <str>'",
            example=["cli: -tool_format 'yosys tcl'",
                     "api: chip.set('tool', 'yosys', 'format', 'tcl')"],
            help=trim("""
            File format for tool manifest handoff.""")))

    schema.insert(
        'licenseserver', 'default',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            pernode=PerNode.OPTIONAL,
            shorthelp="Tool: license servers",
            switch="-tool_licenseserver 'name key <str>'",
            example=[
                "cli: -tool_licenseserver 'atask ACME_LICENSE 1700@server'",
                "api: chip.set('tool', 'acme', 'licenseserver', 'ACME_LICENSE', '1700@server')"],
            help=trim("""
            Defines a set of tool specific environment variables used by the executable
            that depend on license key servers to control access. For multiple servers,
            separate each server by a 'colon'. The named license variable are read at
            runtime (:meth:`.run()`) and the environment variables are set.
            """)))


def schema_task(schema):
    schema = EditableSchema(schema)

    schema.insert(
        'warningoff',
        Parameter(
            '[str]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Task: warning filter",
            switch="-tool_task_warningoff 'tool task <str>'",
            example=[
                "cli: -tool_task_warningoff 'verilator lint COMBDLY'",
                "api: chip.set('tool', 'verilator', 'task', 'lint', 'warningoff', 'COMBDLY')"],
            help=trim("""
            A list of tool warnings for which printing should be suppressed.
            Generally this is done on a per design basis after review has
            determined that warning can be safely ignored The code for turning
            off warnings can be found in the specific task reference manual.
            """)))

    schema.insert(
        'regex', 'default',
        Parameter(
            '[str]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Task: regex filter",
            switch="-tool_task_regex 'tool task suffix <str>'",
            example=[
                "cli: -tool_task_regex 'openroad place errors \"'-v ERROR'\"'",
                "api: chip.set('tool', 'openroad', 'task', 'place', 'regex', 'errors', "
                "'-v ERROR')"],
            help=trim("""
            A list of piped together grep commands. Each entry represents a set
            of command line arguments for grep including the regex pattern to
            match. Starting with the first list entry, each grep output is piped
            into the following grep command in the list. Supported grep options
            include ``-v`` and ``-e``. Patterns starting with "-" should be
            directly preceded by the ``-e`` option. The following example
            illustrates the concept.

            UNIX grep:

            .. code-block:: bash

                $ grep WARNING place.log | grep -v "bbox" > place.warnings

            SiliconCompiler::

                chip.set('task', 'openroad', 'regex', 'place', '0', 'warnings',
                         ["WARNING", "-v bbox"])

            The "errors" and "warnings" suffixes are special cases. When set,
            the number of matches found for these regexes will be added to the
            errors and warnings metrics for the task, respectively. This will
            also cause the logfile to be added to the :keypath:`tool, <tool>,
            task, <task>, report` parameter for those metrics, if not already present.""")))

    # Configuration: cli-option, tcl var, env var, file
    schema.insert(
        'option',
        Parameter(
            '[str]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Task: executable options",
            switch="-tool_task_option 'tool task <str>'",
            example=[
                "cli: -tool_task_option 'openroad cts -no_init'",
                "api: chip.set('tool', 'openroad', 'task', 'cts', 'option', '-no_init')"],
            help=trim("""
            List of command line options for the task executable, specified on
            a per task and per step basis. Options must not include spaces.
            For multiple argument options, each option is a separate list element.
            """)))

    schema.insert(
        'var', 'default',
        Parameter(
            '[str]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Task: script variables",
            switch="-tool_task_var 'tool task key <str>'",
            example=[
                "cli: -tool_task_var 'openroad cts myvar 42'",
                "api: chip.set('tool', 'openroad', 'task', 'cts', 'var', 'myvar', '42')"],
            help=trim("""
            Task script variables specified as key value pairs. Variable
            names and value types must match the name and type of task and reference
            script consuming the variable.""")))

    schema.insert(
        'env', 'default',
        Parameter(
            'str',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Task: environment variables",
            switch="-tool_task_env 'tool task env <str>'",
            example=[
                "cli: -tool_task_env 'openroad cts MYVAR 42'",
                "api: chip.set('tool', 'openroad', 'task', 'cts', 'env', 'MYVAR', '42')"],
            help=trim("""
            Environment variables to set for individual tasks. Keys and values
            should be set in accordance with the task's documentation. Most
            tasks do not require extra environment variables to function.""")))

    schema.insert(
        'file', 'default', Parameter(
            '[file]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            copy=True,
            shorthelp="Task: custom setup files",
            switch="-tool_task_file 'tool task key <file>'",
            example=[
                "cli: -tool_task_file 'openroad floorplan macroplace macroplace.tcl'",
                "api: chip.set('tool', 'openroad', 'task', 'floorplan', 'file', 'macroplace', "
                "'macroplace.tcl')"],
            help=trim("""
            Paths to user supplied files mapped to keys. Keys and filetypes must
            match what's expected by the task/reference script consuming the
            file.
            """)))

    schema.insert(
        'dir', 'default',
        Parameter(
            '[dir]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            copy=True,
            shorthelp="Task: custom setup directories",
            switch="-tool_task_dir 'tool task key <dir>'",
            example=[
                "cli: -tool_task_dir 'verilator compile cincludes include'",
                "api: chip.set('tool', 'verilator', 'task', 'compile', 'dir', 'cincludes', "
                "'include')"],
            help=trim("""
            Paths to user supplied directories mapped to keys. Keys must match
            what's expected by the task/reference script consuming the
            directory.
            """)))

    # Definitions of inputs, outputs, requirements
    schema.insert(
        'input',
        Parameter(
            '[file]',
            scope=Scope.JOB,
            pernode=PerNode.REQUIRED,
            shorthelp="Task: input files",
            switch="-tool_task_input 'tool task <file>'",
            example=[
                "cli: -tool_task_input 'openroad place \"place 0 oh_add.def\"'",
                "api: chip.set('tool', 'openroad', 'task', 'place', 'input', 'oh_add.def', "
                "step='place', index='0')"],
            help=trim("""
            List of data files to be copied from previous flowgraph steps 'output'
            directory. The list of steps to copy files from is defined by the
            list defined by the dictionary key :keypath:`flowgraph,<flow>,<step>,<index>,input`.
            All files must be available for flow to continue. If a file
            is missing, the program exists on an error.""")))

    schema.insert(
        'output',
        Parameter(
            '[file]',
            scope=Scope.JOB,
            pernode=PerNode.REQUIRED,
            shorthelp="Task: output files",
            switch="-tool_task_output 'tool task <file>'",
            example=[
                "cli: -tool_task_output 'openroad place \"place 0 oh_add.def\"'",
                "api: chip.set('tool', 'openroad', 'task', 'place', 'output', 'oh_add.def', "
                "step='place', index='0')"],
            help=trim("""
            List of data files written to the 'output' directory of the
            tool/task/step/index used in the keypath. All files must be available
            for flow to continue. If a file is missing, the program exists on an error.""")))

    dest_enum = ['log', 'output', 'none']
    schema.insert(
        'stdout', 'destination',
        Parameter(
            f'<{",".join(dest_enum)}>',
            defvalue='log',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Task: destination for stdout",
            switch="-tool_task_stdout_destination 'tool task <str>'",
            example=["cli: -tool_task_stdout_destination 'ghdl import log'",
                     "api: chip.set('tool', 'ghdl', 'task', 'import', 'stdout', 'destination', "
                     "'log')"],
            help=trim("""
            Defines where to direct the output generated over stdout.
            Supported options are:
            none: the stream generated to STDOUT is ignored.
            log: the generated stream is stored in <step>.<suffix>; if not in quiet mode,
            it is additionally dumped to the display.
            output: the generated stream is stored in outputs/<design>.<suffix>.""")))

    schema.insert(
        'stdout', 'suffix',
        Parameter(
            'str',
            defvalue='log',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Task: file suffix for redirected stdout",
            switch="-tool_task_stdout_suffix 'tool task <str>'",
            example=["cli: -tool_task_stdout_suffix 'ghdl import log'",
                     "api: chip.set('tool', ghdl', 'task', 'import', 'stdout', 'suffix', 'log')"],
            help=trim("""
            Specifies the file extension for the content redirected from stdout.""")))

    schema.insert(
        'stderr', 'destination',
        Parameter(
            f'<{",".join(dest_enum)}>',
            defvalue='log',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Task: destination for stderr",
            switch="-tool_task_stderr_destination 'tool task <str>'",
            example=["cli: -tool_task_stderr_destination 'ghdl import log'",
                     "api: chip.set('tool', ghdl', 'task', 'import', 'stderr', 'destination', "
                     "'log')"],
            help=trim("""
            Defines where to direct the output generated over stderr.
            Supported options are:
            none: the stream generated to STDERR is ignored
            log: the generated stream is stored in <step>.<suffix>; if not in quiet mode,
            it is additionally dumped to the display.
            output: the generated stream is stored in outputs/<design>.<suffix>""")))

    schema.insert(
        'stderr', 'suffix',
        Parameter(
            'str',
            defvalue='log',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Task: file suffix for redirected stderr",
            switch="-tool_task_stderr_suffix 'tool task <str>'",
            example=["cli: -tool_task_stderr_suffix 'ghdl import log'",
                     "api: chip.set('tool', 'ghdl', 'task', 'import', 'stderr', 'suffix', 'log')"],
            help=trim("""
            Specifies the file extension for the content redirected from stderr.""")))

    schema.insert(
        'require',
        Parameter(
            '[str]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Task: parameter requirements",
            switch="-tool_task_require 'tool task <str>'",
            example=[
                "cli: -tool_task_require 'openroad cts design'",
                "api: chip.set('tool', 'openroad', 'task', 'cts', 'require', 'design')"],
            help=trim("""
            List of keypaths to required task parameters. The list is used
            by :meth:`.check_manifest()` to verify that all parameters have been set up before
            step execution begins.""")))

    schema.insert(
        'report', 'default',
        Parameter(
            '[file]',
            scope=Scope.JOB,
            pernode=PerNode.REQUIRED,
            shorthelp="Task: metric report files",
            switch="-tool_task_report 'tool task metric <file>'",
            example=[
                "cli: -tool_task_report 'openroad place holdtns \"place 0 place.log\"'",
                "api: chip.set('tool', 'openroad', 'task', 'place', 'report', 'holdtns', "
                "'place.log', step='place', index='0')"],
            help=trim("""
            List of report files associated with a specific 'metric'. The file path
            specified is relative to the run directory of the current task.""")))

    schema.insert(
        'refdir',
        Parameter(
            '[dir]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Task: script directory",
            switch="-tool_task_refdir 'tool task <dir>'",
            example=[
                "cli: -tool_task_refdir 'yosys syn ./myref'",
                "api: chip.set('tool', 'yosys', 'task', 'syn_asic', 'refdir', './myref')"],
            help=trim("""
            Path to directories containing reference flow scripts, specified
            on a per step and index basis.""")))

    schema.insert(
        'script',
        Parameter(
            '[file]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Task: entry script",
            switch="-tool_task_script 'tool task <file>'",
            example=[
                "cli: -tool_task_script 'yosys syn syn.tcl'",
                "api: chip.set('tool', 'yosys', 'task', 'syn_asic', 'script', 'syn.tcl')"],
            help=trim("""
            Path to the entry script called by the executable specified
            on a per task and per step basis.""")))

    schema.insert(
        'prescript',
        Parameter(
            '[file]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            copy=True,
            shorthelp="Task: pre-step script",
            switch="-tool_task_prescript 'tool task <file>'",
            example=[
                "cli: -tool_task_prescript 'yosys syn syn_pre.tcl'",
                "api: chip.set('tool', 'yosys', 'task', 'syn_asic', 'prescript', 'syn_pre.tcl')"],
            help=trim("""
            Path to a user supplied script to execute after reading in the design
            but before the main execution stage of the step. Exact entry point
            depends on the step and main script being executed. An example
            of a prescript entry point would be immediately before global
            placement.""")))

    schema.insert(
        'postscript',
        Parameter(
            '[file]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            copy=True,
            shorthelp="Task: post-step script",
            switch="-tool_task_postscript 'tool task <file>'",
            example=[
                "cli: -tool_task_postscript 'yosys syn syn_post.tcl'",
                "api: chip.set('tool', 'yosys', 'task', 'syn_asic', 'postscript', 'syn_post.tcl')"],
            help=trim("""
            Path to a user supplied script to execute after the main execution
            stage of the step but before the design is saved.
            Exact entry point depends on the step and main script being
            executed. An example of a postscript entry point would be immediately
            after global placement.""")))

    schema.insert(
        'threads',
        Parameter(
            'int',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Task: thread parallelism",
            switch="-tool_task_threads 'tool task <int>'",
            example=["cli: -tool_task_threads 'magic drc 64'",
                     "api: chip.set('tool', 'magic', 'task', 'drc', 'threads', '64')"],
            help=trim("""
            Thread parallelism to use for execution specified on a per task and per
            step basis. If not specified, SC queries the operating system and sets
            the threads based on the maximum thread count supported by the
            hardware.""")))
