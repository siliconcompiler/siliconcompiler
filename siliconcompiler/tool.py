import contextlib
import copy
import csv
import gzip
import logging
import os
import psutil
import re
import shlex
import shutil
import subprocess
import sys
import time
import yaml

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

from typing import List, Union, Dict, Tuple

from siliconcompiler.schema import BaseSchema, NamedSchema, Journal
from siliconcompiler.schema import EditableSchema, Parameter, PerNode, Scope
from siliconcompiler.schema.parametertype import NodeType
from siliconcompiler.schema.utils import trim

from siliconcompiler import utils, NodeStatus
from siliconcompiler import sc_open
from siliconcompiler import Schema

from siliconcompiler.record import RecordTool
from siliconcompiler.scheduler import SchedulerNode
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
        super().__init__()
        self.set_name(name)

        schema_task(self)

        self.__set_runtime(None)

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict
        """

        return TaskSchema.__name__

    def _from_dict(self, manifest, keypath, version=None):
        if "var" in manifest:
            # collect var keys
            var_keys = [k[0] for k in self.allkeys("var")]

            # collect manifest
            manifest_keys = set(manifest["var"].keys())

            edit = EditableSchema(self)
            for var in sorted(manifest_keys.difference(var_keys)):
                edit.insert("var", var,
                            Parameter.from_dict(
                                manifest["var"][var],
                                keypath=keypath + [var],
                                version=version))
                del manifest["var"][var]

            if not manifest["var"]:
                del manifest["var"]

        return super()._from_dict(manifest, keypath, version)

    @contextlib.contextmanager
    def runtime(self, node, step=None, index=None, relpath=None):
        '''
        Sets the runtime information needed to properly execute a task.
        Note: unstable API

        Args:
            node (:class:`SchedulerNode`): scheduler node for this runtime
        '''
        if node and not isinstance(node, SchedulerNode):
            raise TypeError("node must be a scheduler node")

        obj_copy = copy.copy(self)
        obj_copy.__set_runtime(node, step=step, index=index, relpath=relpath)
        yield obj_copy

    def __set_runtime(self, node: SchedulerNode, step=None, index=None, relpath=None):
        '''
        Sets the runtime information needed to properly execute a task.
        Note: unstable API

        Args:
            node (:class:`SchedulerNode`): scheduler node for this runtime
        '''
        self.__node = node
        self.__chip = None
        self.__schema_full = None
        self.__logger = None
        self.__design_name = None
        self.__design_top = None
        self.__design_top_global = None
        self.__cwd = None
        self.__relpath = relpath
        self.__collection_path = None
        self.__jobdir = None
        if node:
            if step is not None or index is not None:
                raise RuntimeError("step and index cannot be provided with node")

            self.__chip = node.chip
            self.__schema_full = node.chip.schema
            self.__logger = node.chip.logger
            self.__design_name = node.name
            self.__design_top = node.topmodule
            self.__design_top_global = node.topmodule_global
            self.__cwd = node.project_cwd
            self.__collection_path = node.collection_dir
            self.__jobdir = node.workdir

            self.__step = node.step
            self.__index = node.index
        else:
            self.__step = step
            self.__index = index

        self.__schema_record = None
        self.__schema_metric = None
        self.__schema_flow = None
        self.__schema_flow_runtime = None
        self.__schema_tool = None
        if self.__schema_full:
            self.__schema_record = self.__schema_full.get("record", field="schema")
            self.__schema_metric = self.__schema_full.get("metric", field="schema")
            self.__schema_tool = self._parent()._parent()

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

            self.__schema_flow_runtime = RuntimeFlowgraph(
                self.__schema_flow,
                from_steps=set([step for step, _ in self.__schema_flow.get_entry_nodes()]),
                prune_nodes=self.__schema_full.get('option', 'prune'))

    @property
    def design_name(self) -> str:
        '''
        Returns:
            name of the design
        '''
        return self.__design_name

    @property
    def design_topmodule(self) -> str:
        '''
        Returns:
            top module of the design
        '''
        return self.__design_top

    @property
    def node(self) -> SchedulerNode:
        """
        Returns:
            the scheduler node for the current runtime
        """
        return self.__node

    @property
    def step(self) -> str:
        '''
        Returns:
            step for the current runtime
        '''

        return self.__step

    @property
    def index(self) -> str:
        '''
        Returns:
            index for the current runtime
        '''

        return self.__index

    def tool(self) -> str:
        '''
        Returns:
            tool name
        '''

        raise NotImplementedError("tool name must be implemented by the child class")

    def task(self) -> str:
        '''
        Returns:
            task name
        '''

        raise NotImplementedError("task name must be implemented by the child class")

    @property
    def logger(self) -> logging.Logger:
        '''
        Returns:
            logger
        '''
        return self.__logger

    @property
    def nodeworkdir(self) -> str:
        """
        Path to the node working directory
        """
        return self.__jobdir

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
        elif type == "runtimeflow":
            return self.__schema_flow_runtime
        elif type == "tool":
            return self.__schema_tool
        else:
            raise ValueError(f"{type} is not a schema section")

    def get_logpath(self, log: str) -> str:
        """
        Returns the relative path to the requested log.
        """
        return os.path.relpath(self.__node.get_log(log), self.__jobdir)

    def has_breakpoint(self) -> bool:
        '''
        Returns:
            True if this task has a breakpoint associated with it
        '''
        return self.schema().get("option", "breakpoint", step=self.__step, index=self.__index)

    def get_exe(self) -> str:
        '''
        Determines the absolute path for the specified executable.

        Raises:
            :class:`TaskExecutableNotFound`: if executable not found.

        Returns:
            path to executable, or None if not specified
        '''

        exe = self.schema("tool").get('exe')

        if exe is None:
            return None

        # Collect path
        env = self.get_runtime_environmental_variables(include_path=True)

        fullexe = shutil.which(exe, path=env["PATH"])

        if not fullexe:
            raise TaskExecutableNotFound(f"{exe} could not be found")

        return fullexe

    def get_exe_version(self) -> str:
        '''
        Gets the version of the specified executable.

        Raises:
            :class:`TaskExecutableNotFound`: if executable not found.
            :class:`NotImplementedError`: if :meth:`.parse_version` has not be implemented.

        Returns:
            version determined by :meth:`.parse_version`.
        '''

        veropt = self.schema("tool").get('vswitch')
        if not veropt:
            return None

        exe = self.get_exe()
        if not exe:
            return None

        exe_path, exe_base = os.path.split(exe)

        cmdlist = [exe]
        cmdlist.extend(veropt)

        self.__logger.debug(f'Running {self.tool()}/{self.task()} version check: '
                            f'{" ".join(cmdlist)}')

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
            raise NotImplementedError(f'{self.tool()}/{self.task()} does not implement '
                                      'parse_version()')
        except Exception as e:
            self.__logger.error(f'{self.tool()}/{self.task()} failed to parse version string: '
                                f'{proc.stdout}')
            raise e from None

        self.__logger.info(f"Tool '{exe_base}' found with version '{version}' "
                           f"in directory '{exe_path}'")

        return version

    def check_exe_version(self, reported_version) -> bool:
        '''
        Check if the reported version matches the versions specified in
        :keypath:`tool,<tool>,version`.

        Args:
            reported_version (str): version to check

        Returns:
            True if the version matched, false otherwise

        '''

        spec_sets = self.schema("tool").get('version', step=self.__step, index=self.__index)
        if not spec_sets:
            # No requirement so always true
            return True

        for spec_set in spec_sets:
            split_specs = [s.strip() for s in spec_set.split(",") if s.strip()]
            specs_list = []
            for spec in split_specs:
                match = re.match(TaskSchema.__parse_version_check, spec)
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
                self.__logger.error(f'Unable to normalize version for {self.tool()}/{self.task()}: '
                                    f'{reported_version}')
                raise e from None

            try:
                version = Version(normalized_version)
            except InvalidVersion:
                self.__logger.error(f'Version {normalized_version} reported by '
                                    f'{self.tool()}/{self.task()} does not match standard.')
                return False

            try:
                normalized_spec_list = [
                    f'{op}{self.normalize_version(ver)}' for op, ver in specs_list]
                normalized_specs = ','.join(normalized_spec_list)
            except Exception as e:
                self.__logger.error(f'Unable to normalize versions for '
                                    f'{self.tool()}/{self.task()}: '
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
        self.__logger.error(f"Version check failed for {self.tool()}/{self.task()}. "
                            "Check installation.")
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
        for lic_env in self.schema("tool").getkeys('licenseserver'):
            license_file = self.schema("tool").get('licenseserver', lic_env,
                                                   step=self.__step, index=self.__index)
            if license_file:
                envvars[lic_env] = ':'.join(license_file)

        if include_path:
            path = self.schema("tool").find_files(
                "path", step=self.__step, index=self.__index,
                cwd=self.__cwd,
                collection_dir=self.__collection_path,
                missing_ok=True)

            envvars["PATH"] = os.getenv("PATH", os.defpath)

            if path:
                envvars["PATH"] = path + os.pathsep + envvars["PATH"]

            # Forward additional variables
            for var in ('LD_LIBRARY_PATH',):
                val = os.getenv(var, None)
                if val:
                    envvars[var] = val

        # Add task specific vars
        for env in self.getkeys("env"):
            envvars[env] = self.get("env", env)

        return envvars

    def get_runtime_arguments(self):
        '''
        Constructs the arguments needed to run the task.

        Returns:
            command (list)
        '''

        cmdargs = []
        try:
            if self.__relpath:
                args = []
                for arg in self.runtime_options():
                    arg = str(arg)
                    if os.path.isabs(arg) and os.path.exists(arg):
                        args.append(os.path.relpath(arg, self.__relpath))
                    else:
                        args.append(arg)
            else:
                args = self.runtime_options()

            cmdargs.extend(args)
        except Exception as e:
            self.__logger.error(f'Failed to get runtime options for {self.tool()}/{self.task()}')
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

        replay_opts["executable"] = self.schema("tool").get('exe')
        replay_opts["step"] = self.__step
        replay_opts["index"] = self.__index
        replay_opts["cfg_file"] = f"inputs/{self.__design_name}.pkg.json"
        replay_opts["node_only"] = 0 if replay_opts["executable"] else 1

        vswitch = self.schema("tool").get('vswitch')
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

    def __write_yaml_manifest(self, fout, manifest):
        class YamlIndentDumper(yaml.Dumper):
            def increase_indent(self, flow=False, indentless=False):
                return super().increase_indent(flow=flow, indentless=indentless)

        fout.write(yaml.dump(manifest.getdict(), Dumper=YamlIndentDumper,
                             default_flow_style=False))

    def get_tcl_variables(self, manifest: BaseSchema = None) -> Dict[str, str]:
        """
        Get a dictionary of variables to define for the task in the tcl manifest

        Args:
            manifest (:class`.BaseSchema`): manifest to retrieve values from

        Returns:
            dict of variable name and value
        """

        if manifest is None:
            manifest = self.schema()

        vars = {
            "sc_tool": NodeType.to_tcl(self.tool(), "str"),
            "sc_task": NodeType.to_tcl(self.task(), "str"),
            "sc_topmodule": NodeType.to_tcl(self.design_topmodule, "str")
        }

        refdir = manifest.get("tool", self.tool(), "task", self.task(), "refdir", field=None)
        if refdir.get(step=self.__step, index=self.__index):
            vars["sc_refdir"] = refdir.gettcl(step=self.__step, index=self.__index)

        return vars

    def __write_tcl_manifest(self, fout, manifest):
        template = utils.get_file_template('tcl/manifest.tcl.j2')
        tcl_set_cmds = []
        for key in sorted(manifest.allkeys()):
            # print out all non default values
            if 'default' in key:
                continue

            param = manifest.get(*key, field=None)

            # create a TCL dict
            keystr = ' '.join([NodeType.to_tcl(keypart, 'str') for keypart in key])

            valstr = param.gettcl(step=self.__step, index=self.__index)
            if valstr is None:
                continue

            # Ensure empty values get something
            if valstr == '':
                valstr = '{}'

            tcl_set_cmds.append(f"dict set sc_cfg {keystr} {valstr}")

        if template:
            fout.write(template.render(manifest_dict='\n'.join(tcl_set_cmds),
                                       scroot=os.path.abspath(
                                            os.path.join(os.path.dirname(__file__))),
                                       toolvars=self.get_tcl_variables(manifest),
                                       record_access="get" in Journal.access(self).get_types(),
                                       record_access_id=Schema._RECORD_ACCESS_IDENTIFIER))
        else:
            for cmd in tcl_set_cmds:
                fout.write(cmd + '\n')
            fout.write('\n')

    def __write_csv_manifest(self, fout, manifest):
        csvwriter = csv.writer(fout)
        csvwriter.writerow(['Keypath', 'Value'])

        for key in sorted(manifest.allkeys()):
            keypath = ','.join(key)
            param = manifest.get(*key, field=None)
            if param.get(field="pernode").is_never():
                value = param.get()
            else:
                value = param.get(step=self.__step, index=self.__index)

            if isinstance(value, (set, list)):
                for item in value:
                    csvwriter.writerow([keypath, item])
            else:
                csvwriter.writerow([keypath, value])

    def write_task_manifest(self, directory, backup=True):
        '''
        Write the manifest needed for the task

        Args:
            directory (path): directory to write the manifest into.
            backup (bool): if True and an existing manifest is found a backup is kept.
        '''

        suffix = self.schema("tool").get('format')
        if not suffix:
            return

        manifest_path = os.path.join(directory, f"sc_manifest.{suffix}")

        if backup and os.path.exists(manifest_path):
            shutil.copyfile(manifest_path, f'{manifest_path}.bak')

        # Generate abs paths
        schema = self.__abspath_schema()

        if re.search(r'\.json(\.gz)?$', manifest_path):
            schema.write_manifest(manifest_path)
        else:
            try:
                # format specific dumping
                if manifest_path.endswith('.gz'):
                    fout = gzip.open(manifest_path, 'wt', encoding='UTF-8')
                elif re.search(r'\.csv$', manifest_path):
                    # Files written using csv library should be opened with newline=''
                    # https://docs.python.org/3/library/csv.html#id3
                    fout = open(manifest_path, 'w', newline='')
                else:
                    fout = open(manifest_path, 'w')

                if re.search(r'(\.yaml|\.yml)(\.gz)?$', manifest_path):
                    self.__write_yaml_manifest(fout, schema)
                elif re.search(r'\.tcl(\.gz)?$', manifest_path):
                    self.__write_tcl_manifest(fout, schema)
                elif re.search(r'\.csv(\.gz)?$', manifest_path):
                    self.__write_csv_manifest(fout, schema)
                else:
                    raise ValueError(f"{manifest_path} is not a recognized path type")
            finally:
                fout.close()

    def __abspath_schema(self):
        root = self.schema()
        schema = root.copy()

        strict = root.get("option", "strict")
        root.set("option", "strict", False)

        for keypath in root.allkeys():
            paramtype = schema.get(*keypath, field='type')
            if 'file' not in paramtype and 'dir' not in paramtype:
                # only do something if type is file or dir
                continue

            for value, step, index in root.get(*keypath, field=None).getvalues():
                if not value:
                    continue
                abspaths = root.find_files(*keypath, missing_ok=True, step=step, index=index)
                if isinstance(abspaths, (set, list)) and None in abspaths:
                    # Lists may not contain None
                    schema.set(*keypath, [], step=step, index=index)
                else:
                    if self.__relpath:
                        if isinstance(abspaths, (set, list)):
                            abspaths = [os.path.relpath(path, self.__relpath) for path in abspaths]
                        else:
                            abspaths = os.path.relpath(abspaths, self.__relpath)
                    schema.set(*keypath, abspaths, step=step, index=index)

        root.set("option", "strict", strict)

        return schema

    def __get_io_file(self, io_type):
        '''
        Get the runtime destination for the io type.

        Args:
            io_type (str): name of io type
        '''
        suffix = self.get(io_type, "suffix")
        destination = self.get(io_type, "destination")

        io_file = None
        io_log = False
        if destination == 'log':
            io_file = f"{self.__step}.{suffix}"
            io_log = True
        elif destination == 'output':
            io_file = os.path.join('outputs', f"{self.__design_top_global}.{suffix}")
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
        self.__logger.info(f'Waiting for {self.tool()}/{self.task()} to exit...')
        try:
            proc.wait(timeout=TERMINATE_TIMEOUT)
        except subprocess.TimeoutExpired:
            if proc.poll() is None:
                self.__logger.warning(f'{self.tool()}/{self.task()} did not exit within '
                                      f'{TERMINATE_TIMEOUT} seconds. Terminating...')
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
                self.__logger.error(f'Failed in run() for {self.tool()}/{self.task()}: {e}')
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
                        open(stdout_file, 'r', errors='replace') as stdout_reader, \
                        open(stderr_file, 'w') as stderr_writer, \
                        open(stderr_file, 'r', errors='replace') as stderr_reader:
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
            if key.startswith("_TaskSchema__"):
                del state[key]

        return state

    def __setstate__(self, state):
        self.__dict__ = state

        # Reinit runtime information
        self.__set_runtime(None)

    def get_output_files(self):
        return set(self.get("output"))

    def get_files_from_input_nodes(self):
        """
        Returns a dictionary of files with the node they originated from
        """

        nodes = self.schema("runtimeflow").get_nodes()

        inputs = {}
        for in_step, in_index in self.schema("flow").get(self.step, self.index, 'input'):
            if (in_step, in_index) not in nodes:
                # node has been pruned so will not provide anything
                continue

            in_tool = self.schema("flow").get(in_step, in_index, "tool")
            in_task = self.schema("flow").get(in_step, in_index, "task")

            task_obj = self.schema().get("tool", in_tool, "task", in_task, field="schema")

            if self.schema("record").get('status', step=in_step, index=in_index) == \
                    NodeStatus.SKIPPED:
                with task_obj.runtime(self.__node.switch_node(in_step, in_index)) as task:
                    for file, nodes in task.get_files_from_input_nodes().items():
                        inputs.setdefault(file, []).extend(nodes)
                continue

            for output in NamedSchema.get(task_obj, "output", step=in_step, index=in_index):
                inputs.setdefault(output, []).append((in_step, in_index))

        return inputs

    def compute_input_file_node_name(self, filename, step, index):
        """
        Generate a unique name for in input file based on the originating node.

        Args:
            filename (str): name of inputfile
            step (str): Step name
            index (str): Index name
        """

        _, file_type = os.path.splitext(filename)

        if file_type:
            base = filename
            total_ext = []
            while file_type:
                base, file_type = os.path.splitext(base)
                total_ext.append(file_type)

            total_ext.reverse()

            return f'{base}.{step}{index}{"".join(total_ext)}'
        else:
            return f'{filename}.{step}{index}'

    def add_parameter(self, name, type, help, defvalue=None, **kwargs):
        '''
        Adds a parameter to the task definition.

        Args:
            name (str): name of parameter
            type (str): schema type of the parameter
            help (str): help string for this parameter
            defvalue (any): default value for the parameter
        '''
        help = trim(help)
        param = Parameter(
            type,
            **kwargs,
            defvalue=defvalue,
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp=help,
            help=help
        )

        EditableSchema(self).insert("var", name, param)

        return param

    ###############################################################
    # Task settings
    ###############################################################
    def add_required_tool_key(self, *key: str, step: str = None, index: str = None):
        '''
        Adds a required tool keypath to the task driver.

        Args:
            key (list of str): required key path
        '''
        return self.add_required_key(self, *key, step=step, index=index)

    def add_required_key(self, obj: Union[BaseSchema, str], *key: str,
                         step: str = None, index: str = None):
        '''
        Adds a required keypath to the task driver.

        Args:
            obj (:class:`BaseSchema` or str): if this is a string it will be considered
                part of the key, otherwise the keypath to the obj will be prepended to
                the key
            key (list of str): required key path
        '''

        if isinstance(obj, BaseSchema):
            key = (*obj._keypath, *key)
        else:
            key = (obj, *key)

        if any([not isinstance(k, str) for k in key]):
            raise ValueError("key can only contain strings")

        return self.add("require", ",".join(key), step=step, index=index)

    def set_threads(self, max_threads: int = None,
                    step: str = None, index: str = None,
                    clobber: bool = False):
        """
        Sets the requested thread count for the task

        Args:
            max_threads (int): if provided the requested thread count
                will be set this value, otherwise the current machines
                core count will be used.
            clobber (bool): overwrite existing value
        """
        if max_threads is None or max_threads <= 0:
            max_threads = utils.get_cores(None)

        return self.set("threads", max_threads, step=step, index=index, clobber=clobber)

    def get_threads(self, step: str = None, index: str = None) -> int:
        """
        Returns the number of threads requested.
        """
        return self.get("threads", step=step, index=index)

    def add_commandline_option(self, option: Union[List[str], str],
                               step: str = None, index: str = None,
                               clobber: bool = False):
        """
        Add to the command line options for the task

        Args:
            option (list of str or str): options to add to the commandline
            clobber (bool): overwrite existing value
        """

        if clobber:
            return self.set("option", option, step=step, index=index)
        else:
            return self.add("option", option, step=step, index=index)

    def get_commandline_options(self, step: str = None, index: str = None) -> List[str]:
        """
        Returns the command line options specified
        """
        return self.get("option", step=step, index=index)

    def add_input_file(self, file: str = None, ext: str = None,
                       step: str = None, index: str = None,
                       clobber: bool = False):
        """
        Add a required input file from the previous step in the flow.
        file and ext are mutually exclusive.

        Args:
            file (str): full filename
            ext (str): file extension, if specified, the filename will be <top>.<ext>
            clobber (bool): overwrite existing value
        """
        if file and ext:
            raise ValueError("only file or ext can be specified")

        if ext:
            file = f"{self.design_topmodule}.{ext}"

        if clobber:
            return self.set("input", file, step=step, index=index)
        else:
            return self.add("input", file, step=step, index=index)

    def add_output_file(self, file: str = None, ext: str = None,
                        step: str = None, index: str = None,
                        clobber: bool = False):
        """
        Add an output file that this task will produce
        file and ext are mutually exclusive.

        Args:
            file (str): full filename
            ext (str): file extension, if specified, the filename will be <top>.<ext>
            clobber (bool): overwrite existing value
        """
        if file and ext:
            raise ValueError("only file or ext can be specified")

        if ext:
            file = f"{self.design_topmodule}.{ext}"

        if clobber:
            return self.set("output", file, step=step, index=index)
        else:
            return self.add("output", file, step=step, index=index)

    def set_environmentalvariable(self, name: str, value: str,
                                  step: str = None, index: str = None,
                                  clobber: bool = False):
        return self.set("env", name, value, step=step, index=index, clobber=clobber)

    def add_prescript(self, script: str, dataroot: str = None,
                      step: str = None, index: str = None,
                      clobber: bool = False):
        if not dataroot:
            dataroot = self._get_active("package")
        with self._active(package=dataroot):
            if clobber:
                return self.set("prescript", script, step=step, index=index)
            else:
                return self.add("prescript", script, step=step, index=index)

    def add_postscript(self, script: str, dataroot: str = None,
                       step: str = None, index: str = None,
                       clobber: bool = False):
        if not dataroot:
            dataroot = self._get_active("package")
        with self._active(package=dataroot):
            if clobber:
                return self.set("postscript", script, step=step, index=index)
            else:
                return self.add("postscript", script, step=step, index=index)

    def has_prescript(self, step: str = None, index: str = None) -> bool:
        if self.get("prescript", step=step, index=index):
            return True
        return False

    def has_postscript(self, step: str = None, index: str = None) -> bool:
        if self.get("postscript", step=step, index=index):
            return True
        return False

    def set_refdir(self, dir: str, dataroot: str = None,
                   step: str = None, index: str = None,
                   clobber: bool = False):
        if not dataroot:
            dataroot = self._get_active("package")
        with self._active(package=dataroot):
            return self.set("refdir", dir, step=step, index=index, clobber=clobber)

    def set_script(self, script: str, dataroot: str = None,
                   step: str = None, index: str = None,
                   clobber: bool = False):
        if not dataroot:
            dataroot = self._get_active("package")
        with self._active(package=dataroot):
            return self.set("script", script, step=step, index=index, clobber=clobber)

    def add_regex(self, type: str, regex: str,
                  step: str = None, index: str = None,
                  clobber: bool = False):
        if clobber:
            return self.set("regex", type, regex, step=step, index=index)
        else:
            return self.add("regex", type, regex, step=step, index=index)

    def set_logdestination(self, type: str, dest: str, suffix: str = None,
                           step: str = None, index: str = None,
                           clobber: bool = False):
        rets = []
        rets.append(self.set(type, "destination", dest, step=step, index=index, clobber=clobber))
        if suffix:
            rets.append(self.set(type, "suffix", suffix, step=step, index=index, clobber=clobber))
        return rets

    def add_warningoff(self, type: str, step: str = None, index: str = None, clobber: bool = False):
        if clobber:
            return self.set("warningoff", type, step=step, index=index)
        else:
            return self.add("warningoff", type, step=step, index=index)

    ###############################################################
    # Tool settings
    ###############################################################
    def set_exe(self, exe: str = None, vswitch: List[str] = None, format: str = None,
                clobber: bool = False):
        rets = []
        if exe:
            rets.append(self.schema("tool").set("exe", exe, clobber=clobber))
        if vswitch:
            switches = self.add_vswitch(vswitch, clobber=clobber)
            if not isinstance(switches, list):
                switches = list(switches)
            rets.extend(switches)
        if format:
            rets.append(self.schema("tool").set("format", format, clobber=clobber))
        return rets

    def set_path(self, path: str, dataroot: str = None,
                 step: str = None, index: str = None,
                 clobber: bool = False):
        if not dataroot:
            dataroot = self.schema("tool")._get_active("package")
        with self.schema("tool")._active(package=dataroot):
            return self.schema("tool").set("path", path, step=step, index=index, clobber=clobber)

    def add_version(self, version: str, step: str = None, index: str = None, clobber: bool = False):
        if clobber:
            return self.schema("tool").set("version", version, step=step, index=index)
        else:
            return self.schema("tool").add("version", version, step=step, index=index)

    def add_vswitch(self, switch: str, clobber: bool = False):
        if clobber:
            return self.schema("tool").set("vswitch", switch)
        else:
            return self.schema("tool").add("vswitch", switch)

    def add_licenseserver(self, name: str, server: str,
                          step: str = None, index: str = None,
                          clobber: bool = False):
        if clobber:
            return self.schema("tool").set("licenseserver", name, server, step=step, index=index)
        else:
            return self.schema("tool").add("licenseserver", name, server, step=step, index=index)

    def add_sbom(self, version: str, sbom: str, dataroot: str = None, clobber: bool = False):
        if not dataroot:
            dataroot = self.schema("tool")._get_active("package")
        with self.schema("tool")._active(package=dataroot):
            if clobber:
                return self.schema("tool").set("sbom", version, sbom)
            else:
                return self.schema("tool").add("sbom", version, sbom)

    def record_metric(self, metric, value, source_file=None, source_unit=None):
        '''
        Records a metric and associates the source file with it.

        Args:
            metric (str): metric to record
            value (float/int): value of the metric that is being recorded
            source (str): file the value came from
            source_unit (str): unit of the value, if not provided it is assumed to have no units

        Examples:
            >>> self.record_metric('cellarea', 500.0, 'reports/metrics.json', \\
                    source_units='um^2')
            Records the metric cell area and notes the source as 'reports/metrics.json'
        '''

        if metric not in self.schema("metric").getkeys():
            self.logger.warning(f"{metric} is not a valid metric")
            return

        self.schema("metric").record(self.__step, self.__index, metric, value, unit=source_unit)
        if source_file:
            self.add("report", metric, source_file)

    def get_fileset_file_keys(self, filetype: str) -> List[Tuple[NamedSchema, Tuple[str]]]:
        """
        Collect a set of keys for a particular filetype.

        Args:
            filetype (str): Name of the filetype

        Returns:
            list of (object, keypath)
        """
        if not isinstance(filetype, str):
            raise TypeError("filetype must be a string")

        keys = []
        for obj, fileset in self.schema().get_filesets():
            key = ("fileset", fileset, "file", filetype)
            if obj.valid(*key, check_complete=True):
                keys.append((obj, key))
        return keys

    ###############################################################
    # Schema
    ###############################################################
    def get(self, *keypath, field='value', step: str = None, index: str = None):
        if not step:
            step = self.__step
        if not index:
            index = self.__index
        return super().get(*keypath, field=field, step=step, index=index)

    def set(self, *args, field='value', step: str = None, index: str = None, clobber=True):
        if not step:
            step = self.__step
        if not index:
            index = self.__index
        return super().set(*args, field=field, clobber=clobber, step=step, index=index)

    def add(self, *args, field='value', step: str = None, index: str = None):
        if not step:
            step = self.__step
        if not index:
            index = self.__index
        return super().add(*args, field=field, step=step, index=index)

    def unset(self, *args, step: str = None, index: str = None):
        if not step:
            step = self.__step
        if not index:
            index = self.__index
        return super().unset(*args, step=step, index=index)

    def find_files(self, *keypath, missing_ok=False, step=None, index=None):
        if not step:
            step = self.__step
        if not index:
            index = self.__index
        return super().find_files(*keypath, missing_ok=missing_ok,
                                  step=step, index=index,
                                  collection_dir=self.__collection_path,
                                  cwd=self.__cwd)

    def _find_files_search_paths(self, keypath, step, index):
        paths = super()._find_files_search_paths(keypath, step, index)
        if keypath == "script":
            paths.extend(self.find_files("refdir", step=step, index=index))
        elif keypath == "input":
            paths.append(os.path.join(self._parent(root=True).getworkdir(step=step, index=index),
                                      "inputs"))
        elif keypath == "report":
            paths.append(os.path.join(self._parent(root=True).getworkdir(step=step, index=index),
                                      "report"))
        elif keypath == "output":
            paths.append(os.path.join(self._parent(root=True).getworkdir(step=step, index=index),
                                      "outputs"))
        return paths

    ###############################################################
    # Task methods
    ###############################################################
    def parse_version(self, stdout):
        raise NotImplementedError("must be implemented by the implementation class")

    def normalize_version(self, version):
        return version

    def setup(self):
        pass

    def select_input_nodes(self):
        return self.schema("runtimeflow").get_node_inputs(
            self.__step, self.__index, record=self.schema("record"))

    def pre_process(self):
        pass

    def runtime_options(self):
        cmdargs = []
        cmdargs.extend(self.get("option"))

        script = self.find_files('script', missing_ok=True)

        if script:
            cmdargs.extend(script)

        return cmdargs

    def run(self):
        raise NotImplementedError("must be implemented by the implementation class")

    def post_process(self):
        pass


class ASICTaskSchema(TaskSchema):
    @property
    def mainlib(self):
        mainlib = self.schema().get("asic", "mainlib")
        if not mainlib:
            raise ValueError("mainlib has not been defined in [asic,mainlib]")
        if mainlib not in self.schema().getkeys("library"):
            raise LookupError(f"{mainlib} has not been loaded")
        return self.schema().get("library", mainlib, field="schema")

    @property
    def pdk(self):
        pdk = self.mainlib.get("asic", "pdk")
        if not pdk:
            raise ValueError("pdk has not been defined in "
                             f"[{','.join([*self.mainlib._keypath, 'asic', 'pdk'])}]")
        if pdk not in self.schema().getkeys("library"):
            raise LookupError(f"{pdk} has not been loaded")
        return self.schema().get("library", pdk, field="schema")

    def set_asic_var(self,
                     key: str,
                     defvalue=None,
                     check_pdk: bool = True,
                     require_pdk: bool = False,
                     pdk_key: str = None,
                     check_mainlib: bool = True,
                     require_mainlib: bool = False,
                     mainlib_key: str = None,
                     require: bool = False):
        '''
        Set an ASIC parameter based on a prioritized lookup order.

        This method attempts to set a parameter identified by `key` by checking
        values in a specific order:
        1. The main library
        2. The PDK
        3. A provided default value (`defvalue`)

        The first non-empty or non-None value found in this hierarchy will be
        used to set the parameter. If no value is found and `defvalue` is not
        provided, the parameter will not be set unless explicitly required.

        Args:
            key: The string key for the parameter to be set. This key is used
                to identify the parameter within the current object (`self`)
                and, by default, within the main library and PDK.
            defvalue: An optional default value to use if the parameter is not
                found in the main library or PDK. If `None` and the parameter
                is not found, it will not be set unless `require` is True.
            check_pdk: If `True`, the method will attempt to retrieve the
                parameter from the PDK. Defaults to `True`.
            require_pdk: If `True`, the parameter *must* be defined in the PDK.
                An error will be raised if it's not found and `check_pdk` is `True`.
                Defaults to `False`.
            pdk_key: The specific key to use when looking up the parameter in the
                PDK. If `None`, `key` will be used.
            check_mainlib: If `True`, the method will attempt to retrieve the
                parameter from the main library. Defaults to `True`.
            require_mainlib: If `True`, the parameter *must* be defined in the
                main library. An error will be raised if it's not found and
                `check_mainlib` is `True`. Defaults to `False`.
            mainlib_key: The specific key to use when looking up the parameter in
                the main library. If `None`, `key` will be used.
            require: If `True`, the parameter *must* be set by this method (either
                from a source or `defvalue`). An error will be raised if it cannot
                be set. Defaults to `False`.
        '''
        check_keys = []
        if check_pdk:
            if not pdk_key:
                pdk_key = key
            if self.pdk.valid("tool", self.tool(), pdk_key):
                check_keys.append((self.pdk, ("tool", self.tool(), pdk_key)))
        if check_mainlib:
            if not mainlib_key:
                mainlib_key = key
            if self.mainlib.valid("tool", self.tool(), mainlib_key):
                check_keys.append((self.mainlib, ("tool", self.tool(), mainlib_key)))
        check_keys.append((self, ("var", key)))

        if require_pdk:
            self.add_required_key(self.pdk, "tool", self.tool(), pdk_key)
        if require_mainlib:
            self.add_required_key(self.mainlib, "tool", self.tool(), mainlib_key)
        if require or defvalue is not None:
            self.add_required_key(self, "var", key)

        if self.get("var", key, field=None).is_set(self.step, self.index):
            return

        for obj, keypath in reversed(check_keys):
            if not obj.valid(*keypath):
                continue

            value = obj.get(*keypath)
            if isinstance(value, (list, set, tuple)):
                if not value:
                    continue
            else:
                if value is None:
                    continue
            self.add_required_key(obj, *keypath)
            self.add_required_key(self, "var", key)
            return self.set("var", key, value)
        if defvalue is not None:
            return self.set("var", key, defvalue)


class ToolSchema(NamedSchema):
    def __init__(self, name=None):
        super().__init__()
        self.set_name(name)

        schema_tool(self)

        schema = EditableSchema(self)
        schema.insert("task", "default", TaskSchema(None))

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict
        """

        return ToolSchema.__name__


###########################################################################
# Migration helper
###########################################################################
class ToolSchemaTmp(NamedSchema):
    def __init__(self):
        super().__init__()

        schema_tool(self)

        schema = EditableSchema(self)
        schema.insert("task", "default", TaskSchemaTmp())

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict
        """

        return ToolSchemaTmp.__name__


class TaskSchemaTmp(TaskSchema):
    def __init__(self):
        super().__init__()

    def __module_func(self, name, modules):
        for module in modules:
            method = getattr(module, name, None)
            if method:
                return method
        return None

    def __tool_task_modules(self):
        flow = self._TaskSchema__chip.get('option', 'flow')
        return \
            self._TaskSchema__chip._get_tool_module(self.step, self.index, flow=flow), \
            self._TaskSchema__chip._get_task_module(self.step, self.index, flow=flow)

    @contextlib.contextmanager
    def __in_step_index(self):
        prev_step, prev_index = self._TaskSchema__chip.get('arg', 'step'), \
            self._TaskSchema__chip.get('arg', 'index')
        self._TaskSchema__chip.set('arg', 'step', self.step)
        self._TaskSchema__chip.set('arg', 'index', self.index)
        yield
        self._TaskSchema__chip.set('arg', 'step', prev_step)
        self._TaskSchema__chip.set('arg', 'index', prev_index)

    def tool(self):
        return self.schema("flow").get(self.step, self.index, 'tool')

    def task(self):
        return self.schema("flow").get(self.step, self.index, 'task')

    def get_exe(self):
        if self.tool() == "execute" and self.task() == "exec_input":
            return self.schema("tool").get("exe")
        return super().get_exe()

    def schema(self, type=None):
        if type is None:
            return self._TaskSchema__chip
        return super().schema(type)

    def get_output_files(self):
        _, task = self.__tool_task_modules()
        method = self.__module_func("_gather_outputs", [task])
        if method:
            return method(self._TaskSchema__chip, self.step, self.index)
        return TaskSchema.get_output_files(self)

    def parse_version(self, stdout):
        tool, _ = self.__tool_task_modules()
        method = self.__module_func("parse_version", [tool])
        if method:
            return method(stdout)
        return TaskSchema.parse_version(self, stdout)

    def normalize_version(self, version):
        tool, _ = self.__tool_task_modules()
        method = self.__module_func("normalize_version", [tool])
        if method:
            return method(version)
        return TaskSchema.normalize_version(self, version)

    def generate_replay_script(self, filepath, workdir, include_path=True):
        with self.__in_step_index():
            ret = TaskSchema.generate_replay_script(self, filepath, workdir,
                                                    include_path=include_path)
        return ret

    def setup(self):
        _, task = self.__tool_task_modules()
        method = self.__module_func("setup", [task])
        if method:
            with self.__in_step_index():
                ret = method(self._TaskSchema__chip)
            return ret
        return TaskSchema.setup(self)

    def select_input_nodes(self):
        _, task = self.__tool_task_modules()
        method = self.__module_func("_select_inputs", [task])
        if method:
            with self.__in_step_index():
                ret = method(self._TaskSchema__chip, self.step, self.index)
            return ret
        return TaskSchema.select_input_nodes(self)

    def pre_process(self):
        _, task = self.__tool_task_modules()
        method = self.__module_func("pre_process", [task])
        if method:
            with self.__in_step_index():
                ret = method(self._TaskSchema__chip)
            return ret
        return TaskSchema.pre_process(self)

    def runtime_options(self):
        tool, task = self.__tool_task_modules()
        method = self.__module_func("runtime_options", [task, tool])
        if method:
            with self.__in_step_index():
                ret = TaskSchema.runtime_options(self)
                ret.extend(method(self._TaskSchema__chip))
            return ret
        return TaskSchema.runtime_options(self)

    def run(self):
        _, task = self.__tool_task_modules()
        method = self.__module_func("run", [task])
        if method:
            # Handle logger stdout suppression if quiet
            stdout_handler_level = self._TaskSchema__chip._logger_console.level
            if self._TaskSchema__chip.get('option', 'quiet', step=self.step, index=self.index):
                self._TaskSchema__chip._logger_console.setLevel(logging.CRITICAL)

            with self.__in_step_index():
                retcode = method(self._TaskSchema__chip)

            self._TaskSchema__chip._logger_console.setLevel(stdout_handler_level)

            return retcode
        return TaskSchema.run(self)

    def post_process(self):
        _, task = self.__tool_task_modules()
        method = self.__module_func("post_process", [task])
        if method:
            with self.__in_step_index():
                ret = method(self._TaskSchema__chip)
            return ret
        return TaskSchema.post_process(self)


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
