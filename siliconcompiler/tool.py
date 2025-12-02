import contextlib
import copy
import csv
import gzip
import json
import logging
import os
import psutil
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
import yaml

try:
    # 'resource' is not available on Windows, so we handle its absence gracefully.
    import resource
except ModuleNotFoundError:
    resource = None

try:
    # 'pty' is not available on Windows.
    import pty
except ModuleNotFoundError:
    pty = None

import os.path

from packaging.version import Version, InvalidVersion
from packaging.specifiers import SpecifierSet, InvalidSpecifier

from typing import List, Dict, Tuple, Union, Optional, Set, TextIO, Type, TypeVar, TYPE_CHECKING
from pathlib import Path

from siliconcompiler.schema import BaseSchema, NamedSchema, Journal, DocsSchema, LazyLoad
from siliconcompiler.schema import EditableSchema, Parameter, PerNode, Scope
from siliconcompiler.schema.parametertype import NodeType
from siliconcompiler.schema.utils import trim

from siliconcompiler import utils, NodeStatus, Flowgraph
from siliconcompiler import sc_open
from siliconcompiler.utils import paths

from siliconcompiler.schema_support.pathschema import PathSchema
from siliconcompiler.schema_support.record import RecordTool, RecordSchema
from siliconcompiler.schema_support.metric import MetricSchema
from siliconcompiler.flowgraph import RuntimeFlowgraph

if TYPE_CHECKING:
    from siliconcompiler.scheduler import SchedulerNode
    from siliconcompiler import Project

TTask = TypeVar('TTask')


class TaskError(Exception):
    '''Error indicating that task execution cannot continue and should be terminated.'''
    pass


class TaskTimeout(TaskError):
    '''Error indicating a timeout has occurred during task execution.

    Args:
        timeout (float): The execution time in seconds at which the timeout occurred.
    '''

    def __init__(self, *args, timeout=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = timeout


class TaskExecutableNotFound(TaskError):
    '''Error indicating that the required tool executable could not be found.'''
    pass


class TaskExecutableNotReceived(TaskExecutableNotFound):
    '''Error indicating that the tool executable was not received from a previous step.

    This exception is raised specifically when a task expects to receive an executable
    from an upstream task but no executable file was provided.
    '''
    pass


class TaskSkip(TaskError):
    """
    Error raised to indicate that the current task should be skipped.

    This exception is only intended to be used within the `setup()` and
    `pre_process()` methods of a Task.
    """

    def __init__(self, why: str, *args):
        super().__init__(why, *args)
        self.__why = why

    @property
    def why(self):
        """str: The reason why the task is being skipped."""
        return self.__why


class Task(NamedSchema, PathSchema, DocsSchema):
    """
    A schema class that defines the parameters and methods for a single task
    in a compilation flow.

    This class provides the framework for setting up, running, and post-processing
    a tool. It includes methods for managing executables, versions, runtime
    arguments, and file I/O.
    """
    # Regex for parsing version check strings like ">=1.2.3"
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

    __IO_POLL_INTERVAL: float = 0.1
    __MEM_POLL_INTERVAL: float = 0.5
    __MEMORY_WARN_LIMIT: int = 90

    def __init__(self):
        super().__init__()

        schema_task(self)

        self.__set_runtime(None)

    @classmethod
    def _getdict_type(cls) -> str:
        """Returns the metadata for getdict."""
        return Task.__name__

    def _from_dict(self, manifest: Dict,
                   keypath: Union[List[str], Tuple[str, ...]],
                   version: Optional[Tuple[int, ...]] = None,
                   lazyload: LazyLoad = LazyLoad.ON) \
            -> Tuple[Set[Tuple[str, ...]], Set[Tuple[str, ...]]]:
        """
        Populates the schema from a dictionary, dynamically adding 'var'
        parameters found in the manifest that are not already defined.
        """
        if not lazyload.is_enforced and "var" in manifest:
            # Collect existing and manifest var keys
            var_keys = [k[0] for k in self.allkeys("var")]
            manifest_keys = set(manifest["var"].keys())

            # Add new vars found in the manifest to the schema
            edit = EditableSchema(self)
            for var in sorted(manifest_keys.difference(var_keys)):
                edit.insert("var", var,
                            Parameter.from_dict(
                                manifest["var"][var],
                                keypath=tuple([*keypath, var]),
                                version=version))
                del manifest["var"][var]

            if not manifest["var"]:
                del manifest["var"]

        return super()._from_dict(manifest, keypath, version=version, lazyload=lazyload)

    @contextlib.contextmanager
    def runtime(self, node: "SchedulerNode",
                step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                relpath: Optional[str] = None):
        """
        A context manager to set the runtime information for a task.

        This method creates a temporary copy of the task object with runtime
        information (like the current step, index, and working directories)
        populated from a SchedulerNode. This allows methods within the context
        to access runtime-specific configuration and paths.

        Args:
            node (SchedulerNode): The scheduler node for this runtime context.
        """
        from siliconcompiler.scheduler import SchedulerNode
        if node and not isinstance(node, SchedulerNode):
            raise TypeError("node must be a scheduler node")

        obj_copy = copy.copy(self)
        obj_copy.__set_runtime(node, step=step, index=index, relpath=relpath)
        yield obj_copy

    def __set_runtime(self, node: Optional["SchedulerNode"],
                      step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                      relpath: Optional[str] = None) -> None:
        """
        Private helper to set the runtime information for executing a task.

        Args:
            node (SchedulerNode): The scheduler node for this runtime.
        """
        self.__node: Optional["SchedulerNode"] = node
        self.__schema_full: Optional["Project"] = None
        self.__logger: Optional[logging.Logger] = None
        self.__design_name: Optional[str] = None
        self.__design_top: Optional[str] = None
        self.__relpath: Optional[str] = relpath
        self.__jobdir: Optional[str] = None
        self.__step: Optional[str] = None
        self.__index: Optional[str] = None
        if node:
            if step is not None or index is not None:
                raise RuntimeError("step and index cannot be provided with node")

            self.__schema_full = node.project
            self.__logger = node.project.logger
            self.__design_name = node.name
            self.__design_top = node.topmodule
            self.__jobdir = node.workdir

            self.__step = node.step
            self.__index = node.index
        else:
            self.__step = step
            if isinstance(index, int):
                index = str(index)
            self.__index = index

        self.__schema_record: Optional[RecordSchema] = None
        self.__schema_metric: Optional[MetricSchema] = None
        self.__schema_flow: Optional[Flowgraph] = None
        self.__schema_flow_runtime: Optional[RuntimeFlowgraph] = None
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

            self.__schema_flow_runtime = RuntimeFlowgraph(
                self.__schema_flow,
                from_steps=set([step for step, _ in self.__schema_flow.get_entry_nodes()]),
                prune_nodes=self.__schema_full.get('option', 'prune'))

    @property
    def design_name(self) -> str:
        """str: The name of the design."""
        return self.__design_name

    @property
    def design_topmodule(self) -> str:
        """str: The top module of the design for the current node."""
        return self.__design_top

    @property
    def node(self) -> "SchedulerNode":
        """SchedulerNode: The scheduler node for the current runtime."""
        return self.__node

    @property
    def step(self) -> str:
        """str: The step for the current runtime."""
        return self.__step

    @property
    def index(self) -> str:
        """str: The index for the current runtime."""
        return self.__index

    @property
    def name(self) -> str:
        """str: The name of this task."""
        try:
            return self.task()
        except NotImplementedError:
            return super().name

    def tool(self) -> str:
        """str: The name of the tool associated with this task."""
        raise NotImplementedError("tool name must be implemented by the child class")

    def task(self) -> str:
        """str: The name of this task."""
        raise NotImplementedError("task name must be implemented by the child class")

    @property
    def logger(self) -> logging.Logger:
        """logging.Logger: The logger instance."""
        return self.__logger

    @property
    def nodeworkdir(self) -> str:
        """str: The path to the node's working directory."""
        return self.__jobdir

    @property
    def schema_record(self) -> RecordSchema:
        return self.__schema_record

    @property
    def schema_metric(self) -> MetricSchema:
        return self.__schema_metric

    @property
    def project(self) -> "Project":
        return self.__schema_full

    @property
    def schema_flow(self) -> Flowgraph:
        return self.__schema_flow

    @property
    def schema_flowruntime(self) -> RuntimeFlowgraph:
        return self.__schema_flow_runtime

    def get_logpath(self, log: str) -> str:
        """
        Returns the relative path to a specified log file.

        Args:
            log (str): The type of log file (e.g., 'exe', 'sc').

        Returns:
            str: The relative path to the log file from the node's workdir.
        """
        return os.path.relpath(self.__node.get_log(log), self.__jobdir)

    def has_breakpoint(self) -> bool:
        """
        Checks if a breakpoint is set for this task.

        Returns:
            bool: True if a breakpoint is active, False otherwise.
        """
        return self.project.option.get_breakpoint(step=self.__step, index=self.__index)

    def get_exe(self) -> Optional[str]:
        """
        Determines the absolute path for the task's executable.

        Raises:
            TaskExecutableNotFound: If the executable cannot be found in the system PATH.

        Returns:
            str: The absolute path to the executable, or None if not specified.
        """

        exe: Optional[str] = self.get('exe')

        if exe is None:
            return None

        # Collect PATH from environment variables
        env = self.get_runtime_environmental_variables(include_path=True)

        fullexe = shutil.which(exe, path=env["PATH"])

        if not fullexe:
            self._exe_not_found_handler()
            raise TaskExecutableNotFound(f"{exe} could not be found")

        return fullexe

    def _exe_not_found_handler(self) -> None:
        """
        Helper method to provide additional feedback to users for missing executables
        """
        tools = {}
        with open(os.path.join(os.path.dirname(__file__), "toolscripts", "_tools.json")) as f:
            tools = json.load(f)

        if self.tool() in tools:
            self.logger.info(f"Missing tool can be installed via: \"sc-install {self.tool()}\"")

    def get_exe_version(self) -> Optional[str]:
        """
        Gets the version of the task's executable by running it with a version switch.

        Raises:
            TaskExecutableNotFound: If the executable is not found.
            NotImplementedError: If the `parse_version` method is not implemented.

        Returns:
            str: The parsed version string.
        """

        veropt: Optional[List[str]] = self.get('vswitch')
        if not veropt:
            return None

        exe = self.get_exe()
        if not exe:
            return None

        exe_path, exe_base = os.path.split(exe)

        cmdlist = [exe]
        cmdlist.extend(veropt)

        self.logger.debug(f'Running {self.tool()}/{self.task()} version check: '
                          f'{shlex.join(cmdlist)}')

        proc = subprocess.run(cmdlist,
                              stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              universal_newlines=True)

        if proc.returncode != 0:
            self.logger.warning(f"Version check on '{exe_base}' ended with "
                                f"code {proc.returncode}")

        try:
            version = self.parse_version(proc.stdout)
        except NotImplementedError:
            raise NotImplementedError(f'{self.tool()}/{self.task()} does not implement '
                                      'parse_version()')
        except Exception as e:
            self.logger.error(f'{self.tool()}/{self.task()} failed to parse version string: '
                              f'{proc.stdout}')
            raise e from None

        self.logger.info(f"Tool '{exe_base}' found with version '{version}' "
                         f"in directory '{exe_path}'")

        return version

    def check_exe_version(self, reported_version: str) -> bool:
        """
        Checks if the reported version of a tool satisfies the requirements
        specified in the schema.

        Args:
            reported_version (str): The version string reported by the tool.

        Returns:
            bool: True if the version is acceptable, False otherwise.
        """

        spec_sets: Optional[List[str]] = self.get('version')
        if not spec_sets:
            # No requirement, so always true
            return True

        for spec_set in spec_sets:
            split_specs = [s.strip() for s in spec_set.split(",") if s.strip()]
            specs_list = []
            for spec in split_specs:
                match = re.match(Task.__parse_version_check, spec)
                if match is None:
                    self.logger.warning(f'Invalid version specifier {spec}. '
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
                self.logger.error(f'Unable to normalize version for {self.tool()}/{self.task()}: '
                                  f'{reported_version}')
                raise e from None

            try:
                version = Version(normalized_version)
            except InvalidVersion:
                self.logger.error(f'Version {normalized_version} reported by '
                                  f'{self.tool()}/{self.task()} does not match standard.')
                return False

            try:
                normalized_spec_list = [
                    f'{op}{self.normalize_version(ver)}' for op, ver in specs_list]
                normalized_specs = ','.join(normalized_spec_list)
            except Exception as e:
                self.logger.error(f'Unable to normalize versions for '
                                  f'{self.tool()}/{self.task()}: '
                                  f'{",".join([f"{op}{ver}" for op, ver in specs_list])}')
                raise e from None

            try:
                spec_set = SpecifierSet(normalized_specs)
            except InvalidSpecifier:
                self.logger.error(f'Version specifier set {normalized_specs} '
                                  'does not match standard.')
                return False

            if version in spec_set:
                return True

        allowedstr = '; '.join(spec_sets)
        self.logger.error(f"Version check failed for {self.tool()}/{self.task()}. "
                          "Check installation.")
        self.logger.error(f"Found version {reported_version}, "
                          f"did not satisfy any version specifier set {allowedstr}.")
        return False

    def get_runtime_environmental_variables(self, include_path: bool = True) \
            -> Dict[str, str]:
        """
        Determines the environment variables needed for the task.

        Args:
            include_path (bool): If True, includes the PATH variable.

        Returns:
            dict: A dictionary of environment variable names to their values.
        """

        # Add global environmental vars
        envvars: Dict[str, str] = {}
        for env in self.__schema_full.getkeys('option', 'env'):
            envvars[env] = self.__schema_full.get('option', 'env', env)

        # Add tool-specific license server vars
        for lic_env in self.getkeys('licenseserver'):
            license_file: List[str] = self.get('licenseserver', lic_env)
            if license_file:
                envvars[lic_env] = ':'.join(license_file)

        if include_path:
            path: Optional[str] = self.find_files("path", missing_ok=True)

            envvars["PATH"] = os.getenv("PATH", os.defpath)

            if path:
                envvars["PATH"] = path + os.pathsep + envvars["PATH"]

            # Forward additional variables like LD_LIBRARY_PATH
            for var in ('LD_LIBRARY_PATH',):
                val = os.getenv(var, None)
                if val:
                    envvars[var] = val

        # Add task-specific vars
        for env in self.getkeys("env"):
            envvars[env] = self.get("env", env)

        return envvars

    def get_runtime_arguments(self) -> List[str]:
        """
        Constructs the command-line arguments needed to run the task.

        Returns:
            list: A list of command-line arguments.
        """

        cmdargs = []
        try:
            usr_args = self.runtime_options()
            if usr_args is None:
                raise RuntimeError("runtime_options() returned None")
            if not isinstance(usr_args, (list, set, tuple)):
                raise RuntimeError("runtime_options() must return a list")

            if self.__relpath:
                args = []
                for arg in usr_args:
                    arg = str(arg)
                    if os.path.isabs(arg) and os.path.exists(arg):
                        args.append(os.path.relpath(arg, self.__relpath))
                    else:
                        args.append(arg)
            else:
                args = usr_args

            cmdargs.extend(args)
        except Exception as e:
            self.logger.error(f'Failed to get runtime options for {self.tool()}/{self.task()}')
            raise e from None

        # Cleanup args
        cmdargs = [str(arg).strip() for arg in cmdargs]

        return cmdargs

    def generate_replay_script(self, filepath: str, workdir: str, include_path: bool = True) \
            -> None:
        """
        Generates a shell script to replay the task's execution.

        Args:
            filepath (str): The path to write the replay script to.
            workdir (str): The path to the run's working directory.
            include_path (bool): If True, includes PATH information.
        """
        replay_opts: Dict[str, Optional[Union[Dict[str, str], str, int]]] = {}
        replay_opts["work_dir"] = workdir
        replay_opts["exports"] = self.get_runtime_environmental_variables(include_path=include_path)

        replay_opts["executable"] = self.get('exe')
        replay_opts["step"] = self.__step
        replay_opts["index"] = self.__index
        replay_opts["cfg_file"] = f"inputs/{self.__design_name}.pkg.json"
        replay_opts["node_only"] = 0 if replay_opts["executable"] else 1

        vswitch: Optional[List[str]] = self.get('vswitch')
        if vswitch:
            replay_opts["version_flag"] = shlex.join(vswitch)

        # Regex to detect arguments and file paths for formatting
        arg_test = re.compile(r'^[-+]')
        file_test = re.compile(r'^[/\.]')

        if replay_opts["executable"]:
            format_cmd: List[str] = [replay_opts["executable"]]

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

        # Create replay file from template
        with open(filepath, 'w') as f:
            f.write(utils.get_file_template("replay/replay.sh.j2").render(replay_opts))
            f.write("\n")

        os.chmod(filepath, 0o755)

    def setup_work_directory(self, workdir: str, remove_exist: bool = True) -> None:
        """
        Creates the runtime directories needed to execute a task.

        Args:
            workdir (str): The path to the node's working directory.
            remove_exist (bool): If True, removes the directory if it already exists.
        """

        # Delete existing directory if requested
        if os.path.isdir(workdir) and remove_exist:
            shutil.rmtree(workdir)

        # Create standard subdirectories
        os.makedirs(workdir, exist_ok=True)
        os.makedirs(os.path.join(workdir, 'inputs'), exist_ok=True)
        os.makedirs(os.path.join(workdir, 'outputs'), exist_ok=True)
        os.makedirs(os.path.join(workdir, 'reports'), exist_ok=True)

    def __write_yaml_manifest(self, fout: TextIO, manifest: BaseSchema) -> None:
        """Private helper to write a manifest in YAML format."""
        class YamlIndentDumper(yaml.Dumper):
            def increase_indent(self, flow=False, indentless=False):
                return super().increase_indent(flow=flow, indentless=indentless)

        fout.write(yaml.dump(manifest.getdict(), Dumper=YamlIndentDumper,
                             default_flow_style=False))

    def get_tcl_variables(self, manifest: Optional[BaseSchema] = None) -> Dict[str, str]:
        """
        Gets a dictionary of variables to define for the task in a Tcl manifest.

        Args:
            manifest (BaseSchema, optional): The manifest to retrieve values from.

        Returns:
            dict: A dictionary of variable names and their Tcl-formatted values.
        """

        if manifest is None:
            manifest = self.project

        vars = {
            "sc_tool": NodeType.to_tcl(self.tool(), "str"),
            "sc_task": NodeType.to_tcl(self.task(), "str"),
            "sc_topmodule": NodeType.to_tcl(self.design_topmodule, "str"),
            "sc_designlib": NodeType.to_tcl(self.design_name, "str")
        }

        refdir: Parameter = manifest.get("tool", self.tool(), "task", self.task(), "refdir",
                                         field=None)
        if refdir.get(step=self.__step, index=self.__index):
            vars["sc_refdir"] = refdir.gettcl(step=self.__step, index=self.__index)

        return vars

    def __write_tcl_manifest(self, fout: TextIO, manifest: BaseSchema):
        """Private helper to write a manifest in Tcl format."""
        template = utils.get_file_template('tcl/manifest.tcl.j2')
        tcl_set_cmds = []
        for key in sorted(manifest.allkeys()):
            # Skip default values
            if 'default' in key:
                continue

            param: Parameter = manifest.get(*key, field=None)

            # Create a Tcl dict key string
            keystr = ' '.join([NodeType.to_tcl(keypart, 'str') for keypart in key])

            valstr = param.gettcl(step=self.__step, index=self.__index)
            if valstr is None:
                continue

            # Ensure empty values are represented as empty Tcl lists
            if valstr == '':
                valstr = '{}'

            tcl_set_cmds.append(f"dict set sc_cfg {keystr} {valstr}")

        if template:
            fout.write(template.render(manifest_dict='\n'.join(tcl_set_cmds),
                                       scroot=os.path.abspath(
                                           os.path.join(os.path.dirname(__file__))),
                                       toolvars=self.get_tcl_variables(manifest),
                                       record_access="get" in Journal.access(self).get_types(),
                                       record_access_id="TODO"))
        else:
            for cmd in tcl_set_cmds:
                fout.write(cmd + '\n')
            fout.write('\n')

    def __write_csv_manifest(self, fout: TextIO, manifest: BaseSchema) -> None:
        """Private helper to write a manifest in CSV format."""
        csvwriter = csv.writer(fout)
        csvwriter.writerow(['Keypath', 'Value'])

        for key in sorted(manifest.allkeys()):
            keypath = ','.join(key)
            param: Parameter = manifest.get(*key, field=None)
            if param.get(field="pernode").is_never():
                value = param.get()
            else:
                value = param.get(step=self.__step, index=self.__index)

            if isinstance(value, (set, list)):
                for item in value:
                    csvwriter.writerow([keypath, item])
            else:
                csvwriter.writerow([keypath, value])

    def write_task_manifest(self, directory: str, backup: bool = True) -> None:
        """
        Writes the manifest needed for the task in the format specified by the tool.

        Args:
            directory (str): The directory to write the manifest into.
            backup (bool): If True, backs up an existing manifest.
        """

        suffix = self.get('format')
        if not suffix:
            return

        manifest_path = os.path.join(directory, f"sc_manifest.{suffix}")

        if backup and os.path.exists(manifest_path):
            shutil.copyfile(manifest_path, f'{manifest_path}.bak')

        # Generate a schema with absolute paths for the manifest
        schema = self.__abspath_schema()

        if re.search(r'\.json(\.gz)?$', manifest_path):
            schema.write_manifest(manifest_path)
        else:
            # Format-specific dumping
            if manifest_path.endswith('.gz'):
                fout = gzip.open(manifest_path, 'wt', encoding='UTF-8')
            elif re.search(r'\.csv$', manifest_path):
                fout = open(manifest_path, 'w', newline='')
            else:
                fout = open(manifest_path, 'w')
            try:
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

    def __abspath_schema(self) -> "Project":
        """
        Private helper to create a copy of the schema with all file/dir paths
        converted to absolute paths.
        """
        root = self.project
        schema = root.copy()

        for keypath in root.allkeys():
            if keypath[0] == "history":
                # Ignore history as this is not relevant to the task
                continue

            paramtype: str = schema.get(*keypath, field='type')
            if 'file' not in paramtype and 'dir' not in paramtype:
                continue

            for value, step, index in root.get(*keypath, field=None).getvalues():
                if not value:
                    continue
                abspaths = root.find_files(*keypath, missing_ok=True, step=step, index=index)
                if isinstance(abspaths, (set, list)) and None in abspaths:
                    schema.set(*keypath, [], step=step, index=index)
                else:
                    if self.__relpath:
                        if isinstance(abspaths, (set, list)):
                            abspaths = [os.path.relpath(path, self.__relpath) for path in abspaths
                                        if path]
                        elif abspaths:
                            abspaths = os.path.relpath(abspaths, self.__relpath)
                        else:
                            abspaths = None
                    schema.set(*keypath, abspaths, step=step, index=index)

        return schema

    def __get_io_file(self, io_type: str) -> Tuple[str, bool]:
        """
        Private helper to get the runtime destination for stdout or stderr.

        Args:
            io_type (str): The I/O type ('stdout' or 'stderr').
        """
        suffix = self.get(io_type, "suffix")
        destination = self.get(io_type, "destination")

        io_file = None
        io_log = False
        if destination == 'log':
            io_file = f"{self.__step}.{suffix}"
            io_log = True
        elif destination == 'output':
            io_file = os.path.join('outputs', f"{self.__design_top}.{suffix}")
        elif destination == 'none':
            io_file = os.devnull

        return io_file, io_log

    def __terminate_exe(self, proc: subprocess.Popen) -> None:
        """
        Private helper to terminate a subprocess and its children.

        Args:
            proc (subprocess.Process): The process to terminate.
        """

        def terminate_process(pid: int, timeout: int = 3) -> None:
            """Terminates a process and all its (grand+)children.
            Based on https://psutil.readthedocs.io/en/latest/#psutil.wait_procs and
            https://psutil.readthedocs.io/en/latest/#kill-process-tree."""
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            children.append(parent)
            for p in children:
                try:
                    p.terminate()
                except psutil.NoSuchProcess:
                    pass

            _, alive = psutil.wait_procs(children, timeout=timeout)
            for p in alive:
                p.kill()

        timeout = 5

        terminate_process(proc.pid, timeout=timeout)
        self.logger.info(f'Waiting for {self.tool()}/{self.task()} to exit...')
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if proc.poll() is None:
                self.logger.warning(f'{self.tool()}/{self.task()} did not exit within '
                                    f'{timeout} seconds. Terminating...')
                terminate_process(proc.pid, timeout=timeout)

    def __collect_memory(self, pid) -> Optional[int]:
        try:
            pproc = psutil.Process(pid)
            proc_mem_bytes = pproc.memory_full_info().uss
            for child in pproc.children(recursive=True):
                proc_mem_bytes += child.memory_full_info().uss
            return proc_mem_bytes
        except psutil.Error:
            # Process may have already terminated or been killed.
            # Retain existing memory usage statistics in this case.
            pass
        except PermissionError:
            # OS is preventing access to this information so it cannot
            # be collected
            pass
        return None

    def __check_memory_limit(self, warn_limit: int) -> int:
        try:
            memory_usage = psutil.virtual_memory()
            if memory_usage.percent > warn_limit:
                self.logger.warning(
                    'Current system memory usage is '
                    f'{memory_usage.percent:.1f}%')
                return int(memory_usage.percent + 1)
        except psutil.Error:
            pass
        except PermissionError:
            pass
        return warn_limit

    def run_task(self,
                 workdir: str,
                 quiet: bool,
                 breakpoint: bool,
                 nice: Optional[int],
                 timeout: Optional[int]) -> int:
        """
        Executes the task's main process.

        This method handles the full lifecycle of running the tool, including
        setting up the work directory, writing manifests, redirecting I/O,
        monitoring for timeouts, and recording metrics.

        Args:
            workdir (str): The path to the node's working directory.
            quiet (bool): If True, suppresses execution output.
            breakpoint (bool): If True, attempts to run with a breakpoint.
            nice (int): The POSIX nice level for the process.
            timeout (int): The execution timeout in seconds.

        Returns:
            int: The return code from the execution.
        """

        max_mem_bytes = 0
        cpu_start = time.time()

        # Ensure directories are set up
        self.setup_work_directory(workdir, remove_exist=False)

        # Write task-specific manifest
        self.write_task_manifest(workdir)

        # Get file I/O destinations
        stdout_file, is_stdout_log = self.__get_io_file("stdout")
        stderr_file, is_stderr_log = self.__get_io_file("stderr")

        stdout_print = self.logger.info
        stderr_print = self.logger.error

        def read_stdio(stdout_reader, stderr_reader):
            """Helper to read and print stdout/stderr streams."""
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
            # No executable defined, so call the Python `run()` method
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
                self.logger.error(f'Failed in run() for {self.tool()}/{self.task()}: {e}')
                utils.print_traceback(self.logger, e)
                raise e
            finally:
                with sc_open(stdout_file) as stdout_reader, \
                     sc_open(stderr_file) as stderr_reader:
                    read_stdio(stdout_reader, stderr_reader)

                if resource:
                    try:
                        # Collect peak memory usage of the current process
                        max_mem_bytes = max(
                            max_mem_bytes,
                            1024 * resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                    except (OSError, ValueError, PermissionError):
                        pass
        else:
            # An executable is defined, run it as a subprocess
            cmdlist = self.get_runtime_arguments()

            # Record tool options
            self.schema_record.record_tool(
                self.step, self.index,
                cmdlist, RecordTool.ARGS)

            self.logger.info(shlex.join([os.path.basename(exe), *cmdlist]))

            if not pty and breakpoint:
                breakpoint = False

            if breakpoint and sys.platform in ('darwin', 'linux'):
                # Use pty for interactive breakpoint sessions on POSIX systems
                with open(f"{self.step}.log", 'wb') as log_writer:
                    def read(fd):
                        data = os.read(fd, 1024)
                        log_writer.write(data)
                        return data
                    retcode = pty.spawn([exe, *cmdlist], read)
            else:
                # Standard subprocess execution
                with open(stdout_file, 'w') as stdout_writer, \
                     open(stdout_file, 'r', errors='replace') as stdout_reader, \
                     open(stderr_file, 'w') as stderr_writer, \
                     open(stderr_file, 'r', errors='replace') as stderr_reader:
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

                    memory_warn_limit = Task.__MEMORY_WARN_LIMIT
                    next_collection = None
                    try:
                        while proc.poll() is None:
                            curr_time = time.time()

                            # Monitor subprocess memory usage
                            if next_collection is None or \
                                    next_collection <= curr_time:
                                proc_mem_bytes = self.__collect_memory(proc.pid)
                                if proc_mem_bytes is not None:
                                    max_mem_bytes = max(max_mem_bytes, proc_mem_bytes)
                                next_collection = curr_time + Task.__MEM_POLL_INTERVAL

                                memory_warn_limit = self.__check_memory_limit(memory_warn_limit)

                            read_stdio(stdout_reader, stderr_reader)

                            # Check for timeout
                            duration = curr_time - cpu_start
                            if timeout is not None and duration > timeout:
                                raise TaskTimeout(timeout=duration)

                            time.sleep(Task.__IO_POLL_INTERVAL)
                    except KeyboardInterrupt:
                        self.logger.info("Received ctrl-c.")
                        self.__terminate_exe(proc)
                        raise TaskError
                    except TaskTimeout as e:
                        self.logger.error(f'Task timed out after {e.timeout:.1f} seconds')
                        self.__terminate_exe(proc)
                        raise e from None

                    # Read any remaining I/O
                    read_stdio(stdout_reader, stderr_reader)

                    retcode = proc.returncode

        # Record metrics
        self.schema_record.record_tool(
            self.step, self.index,
            retcode, RecordTool.EXITCODE)

        self.schema_metric.record(
            self.step, self.index,
            'exetime', time.time() - cpu_start, unit='s')
        self.schema_metric.record(
            self.step, self.index,
            'memory', max_mem_bytes, unit='B')

        return retcode

    def __getstate__(self):
        """Custom state for pickling, removing runtime info."""
        state = self.__dict__.copy()
        for key in list(state.keys()):
            if key.startswith("_Task__"):
                del state[key]
        return state

    def __setstate__(self, state):
        """Custom state for unpickling, re-initializing runtime info."""
        self.__dict__ = state
        self.__set_runtime(None)

    def get_output_files(self) -> Set[str]:
        """Gets the set of output files defined for this task."""
        return set(self.get("output"))

    def get_files_from_input_nodes(self) -> Dict[str, List[Tuple[str, str]]]:
        """
        Returns a dictionary of files from input nodes, mapped to the node
        they originated from.
        """
        nodes = self.schema_flowruntime.get_nodes()
        inputs = {}
        for in_step, in_index in self.schema_flow.get(self.step, self.index, 'input'):
            if (in_step, in_index) not in nodes:
                continue

            in_tool = self.schema_flow.get(in_step, in_index, "tool")
            in_task = self.schema_flow.get(in_step, in_index, "task")
            task_obj: Task = self.project.get("tool", in_tool, "task", in_task, field="schema")

            if self.schema_record.get('status', step=in_step, index=in_index) == \
                    NodeStatus.SKIPPED:
                with task_obj.runtime(self.__node.switch_node(in_step, in_index)) as task:
                    for file, nodes in task.get_files_from_input_nodes().items():
                        inputs.setdefault(file, []).extend(nodes)
                continue

            for output in NamedSchema.get(task_obj, "output", step=in_step, index=in_index):
                inputs.setdefault(output, []).append((in_step, in_index))

        return inputs

    def compute_input_file_node_name(self, filename: str, step: str, index: str) -> str:
        """
        Generates a unique name for an input file based on its originating node.

        Args:
            filename (str): The original name of the input file.
            step (str): The step name of the originating node.
            index (str): The index of the originating node.
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

    def add_parameter(self, name: str, type: str, help: str, defvalue=None, **kwargs) -> Parameter:
        """
        Adds a custom parameter ('var') to the task definition.

        Args:
            name (str): The name of the parameter.
            type (str): The schema type of the parameter.
            help (str): The help string for the parameter.
            defvalue: The default value for the parameter.
        """
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
    def add_required_key(self, obj: Union[BaseSchema, str], *key: str,
                         step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        '''
        Adds a required keypath to the task driver. If the key is valid relative to the task object
            the key will be assumed as a task key.

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
            if self.valid(*key, check_complete=True):
                key = (*self._keypath, *key)

        if any([not isinstance(k, str) for k in key]):
            raise ValueError("key can only contain strings")

        return self.add("require", ",".join(key), step=step, index=index)

    def set_threads(self, max_threads: Optional[int] = None,
                    step: Optional[str] = None, index: Optional[Union[str, int]] = None,
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
            max_schema_threads: Optional[int] = self.project.option.scheduler.get("maxthreads")
            if max_schema_threads:
                max_threads = max_schema_threads
            else:
                max_threads = utils.get_cores()

        return self.set("threads", max_threads, step=step, index=index, clobber=clobber)

    def get_threads(self, step: Optional[str] = None,
                    index: Optional[Union[str, int]] = None) -> int:
        """
        Returns the number of threads requested.
        """
        return self.get("threads", step=step, index=index)

    def add_commandline_option(self, option: Union[List[str], str],
                               step: Optional[str] = None, index: Optional[Union[str, int]] = None,
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

    def get_commandline_options(self,
                                step: Optional[str] = None,
                                index: Optional[Union[str, int]] = None) \
            -> List[str]:
        """
        Returns the command line options specified
        """
        return self.get("option", step=step, index=index)

    def add_input_file(self, file: Optional[str] = None, ext: Optional[str] = None,
                       step: Optional[str] = None, index: Optional[Union[str, int]] = None,
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

    def add_output_file(self, file: Optional[str] = None, ext: Optional[str] = None,
                        step: Optional[str] = None, index: Optional[Union[str, int]] = None,
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
                                  step: Optional[str] = None,
                                  index: Optional[Union[str, int]] = None,
                                  clobber: bool = False):
        '''Sets an environment variable for the tool's execution context.

        The specified variable will be set in the shell environment before the
        tool's executable is launched.

        Args:
            name (str): The name of the environment variable (e.g., 'PATH').
            value (str): The value to assign to the variable.
            step (str, optional): The step associated with this setting.
                Defaults to the current step.
            index (str, optional): The index associated with this setting.
                Defaults to the current index.
            clobber (bool): If True, overwrite existing values. Otherwise,
                append to them.

        Returns:
            The schema key that was set.
        '''
        return self.set("env", name, value, step=step, index=index, clobber=clobber)

    def add_prescript(self, script: str, dataroot: Optional[str] = None,
                      step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                      clobber: bool = False):
        '''Adds a script to be executed *before* the main tool command.

        This is useful for pre-processing files or setting up the environment
        in ways that go beyond simple environment variables.

        Args:
            script (str): The path to the pre-execution script.
            dataroot (str, optional): The data root this path is relative to.
                Defaults to the active package.
            step (str, optional): The step associated with this setting.
                Defaults to the current step.
            index (str, optional): The index associated with this setting.
                Defaults to the current index.
            clobber (bool): If True, overwrite existing values. Otherwise,
                append to them.

        Returns:
            The schema key that was set.
        '''
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            if clobber:
                return self.set("prescript", script, step=step, index=index)
            else:
                return self.add("prescript", script, step=step, index=index)

    def add_postscript(self, script: str, dataroot: Optional[str] = None,
                       step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                       clobber: bool = False):
        '''Adds a script to be executed *after* the main tool command.

        This is useful for post-processing tool outputs or performing cleanup
        actions.

        Args:
            script (str): The path to the post-execution script.
            dataroot (str, optional): The data root this path is relative to.
                Defaults to the active package.
            step (str, optional): The step associated with this setting.
                Defaults to the current step.
            index (str, optional): The index associated with this setting.
                Defaults to the current index.
            clobber (bool): If True, overwrite existing values. Otherwise,
                append to them.

        Returns:
            The schema key that was set.
        '''
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            if clobber:
                return self.set("postscript", script, step=step, index=index)
            else:
                return self.add("postscript", script, step=step, index=index)

    def has_prescript(self,
                      step: Optional[str] = None, index: Optional[Union[str, int]] = None) -> bool:
        '''Checks if any pre-execution scripts are configured for the task.

        Args:
            step (str, optional): The step to check. Defaults to the current step.
            index (str, optional): The index to check. Defaults to the current index.

        Returns:
            True if one or more pre-scripts are set, False otherwise.
        '''
        if self.get("prescript", step=step, index=index):
            return True
        return False

    def has_postscript(self,
                       step: Optional[str] = None, index: Optional[Union[str, int]] = None) -> bool:
        '''Checks if any post-execution scripts are configured for the task.

        Args:
            step (str, optional): The step to check. Defaults to the current step.
            index (str, optional): The index to check. Defaults to the current index.

        Returns:
            True if one or more post-scripts are set, False otherwise.
        '''
        if self.get("postscript", step=step, index=index):
            return True
        return False

    def set_refdir(self, dir: Union[Path, str], dataroot: Optional[str] = None,
                   step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                   clobber: bool = False):
        '''Sets the reference directory for tool scripts and auxiliary files.

        This is often used by script-based tools to find helper scripts or
        resource files relative to the main entry script.

        Args:
            dir (str): The path to the reference directory.
            dataroot (str, optional): The data root this path is relative to.
                Defaults to the active package.
            step (str, optional): The step associated with this setting.
                Defaults to the current step.
            index (str, optional): The index associated with this setting.
                Defaults to the current index.
            clobber (bool): If True, overwrite existing values.

        Returns:
            The schema key that was set.
        '''
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            return self.set("refdir", dir, step=step, index=index, clobber=clobber)

    def set_script(self, script: Union[Path, str], dataroot: Optional[str] = ...,
                   step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                   clobber: bool = False):
        '''Sets the main entry script for a script-based tool (e.g., a TCL script).

        Args:
            script (str): The path to the entry script.
            dataroot (str, optional): The data root this path is relative to.
                Defaults to the active package.
            step (str, optional): The step associated with this setting.
                Defaults to the current step.
            index (str, optional): The index associated with this setting.
                Defaults to the current index.
            clobber (bool): If True, overwrite existing values.

        Returns:
            The schema key that was set.
        '''
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            return self.set("script", script, step=step, index=index, clobber=clobber)

    def add_regex(self, type: str, regex: str,
                  step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                  clobber: bool = False):
        '''Adds a regular expression for parsing the tool's log file.

        These regexes are used by the framework to identify errors, warnings,
        and metrics from the tool's standard output.

        Args:
            type (str): The category of the regex (e.g., 'error', 'warning').
            regex (str): The regular expression pattern.
            step (str, optional): The step associated with this setting.
                Defaults to the current step.
            index (str, optional): The index associated with this setting.
                Defaults to the current index.
            clobber (bool): If True, overwrite existing values. Otherwise,
                append to them.

        Returns:
            The schema key that was set.
        '''
        if clobber:
            return self.set("regex", type, regex, step=step, index=index)
        else:
            return self.add("regex", type, regex, step=step, index=index)

    def set_logdestination(self, type: str, dest: str, suffix: Optional[str] = None,
                           step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                           clobber: bool = False):
        '''Configures the destination for log files.

        This method sets where log files are written ('file' or 'api') and
        can specify a custom file suffix.

        Args:
            type (str): The type of log (e.g., 'report', 'metric').
            dest (str): The destination, either 'file' or 'api'.
            suffix (str, optional): A custom suffix for the log file name.
            step (str, optional): The step associated with this setting.
                Defaults to the current step.
            index (str, optional): The index associated with this setting.
                Defaults to the current index.
            clobber (bool): If True, overwrite existing values.

        Returns:
            A list of the schema keys that were set.
        '''
        rets = []
        rets.append(self.set(type, "destination", dest, step=step, index=index, clobber=clobber))
        if suffix:
            rets.append(self.set(type, "suffix", suffix, step=step, index=index, clobber=clobber))
        return rets

    def add_warningoff(self, type: str,
                       step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                       clobber: bool = False):
        '''Adds a warning message or code to be suppressed during log parsing.

        Any warning that matches a regex in this list will be ignored by the
        framework.

        Args:
            type (str): The warning message or code to suppress.
            step (str, optional): The step associated with this setting.
                Defaults to the current step.
            index (str, optional): The index associated with this setting.
                Defaults to the current index.
            clobber (bool): If True, overwrite existing values. Otherwise,
                append to them.

        Returns:
            The schema key that was set.
        '''
        if clobber:
            return self.set("warningoff", type, step=step, index=index)
        else:
            return self.add("warningoff", type, step=step, index=index)

    ###############################################################
    # Tool settings
    ###############################################################
    def set_exe(self, exe: Optional[str] = None, vswitch: Optional[Union[str, List[str]]] = None,
                format: Optional[str] = None,
                step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                clobber: bool = False):
        '''Sets the executable, version switch, and script format for a tool.

        This is a convenience method that bundles the configuration of a tool's
        core executable properties.

        Args:
            exe (str, optional): The name of the tool's executable binary.
            vswitch (List[str], optional): The command-line switch used to
                make the executable print its version (e.g., '--version').
            format (str, optional): The format of the entry script, if any
                (e.g., 'tcl', 'python').
            step (str, optional): The step associated with this setting.
                Defaults to the current step.
            index (str, optional): The index associated with this setting.
                Defaults to the current index.
            clobber (bool): If True, overwrite existing values. Otherwise,
                append to them.

        Returns:
            A list of the schema keys that were set.
        '''
        rets = []
        if exe:
            rets.append(self.set("exe", exe, step=step, index=index, clobber=clobber))
        if vswitch:
            switches = self.add_vswitch(vswitch, step=step, index=index, clobber=clobber)
            if not isinstance(switches, list):
                switches = list(switches)
            rets.extend(switches)
        if format:
            rets.append(self.set("format", format, step=step, index=index, clobber=clobber))
        return rets

    def set_path(self, path: str, dataroot: Optional[str] = None,
                 step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                 clobber: bool = False):
        '''Sets the directory path where the tool's executable is located.

        This path is prepended to the system's PATH environment variable
        during execution.

        Args:
            path (str): The directory path to the tool's executable.
            dataroot (str, optional): The data root this path is relative to.
                Defaults to the active package.
            step (str, optional): The step associated with this setting.
                Defaults to the current step.
            index (str, optional): The index associated with this setting.
                Defaults to the current index.
            clobber (bool): If True, overwrite existing values. Otherwise,
                append to them.

        Returns:
            The schema key that was set.
        '''
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            return self.set("path", path, step=step, index=index, clobber=clobber)

    def add_version(self, version: Union[List[str], str],
                    step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                    clobber: bool = False):
        '''Adds a supported version specifier for the tool.

        SiliconCompiler checks the tool's actual version against these
        specifiers to ensure compatibility. Versions should follow the
        PEP-440 standard (e.g., '>=5.6', '==1.2.3').

        Args:
            version (str): The version specifier string.
            step (str, optional): The step associated with this setting.
                Defaults to the current step.
            index (str, optional): The index associated with this setting.
                Defaults to the current index.
            clobber (bool): If True, overwrite existing values. Otherwise,
                append to them.

        Returns:
            The schema key that was set.
        '''
        if clobber:
            return self.set("version", version, step=step, index=index)
        else:
            return self.add("version", version, step=step, index=index)

    def add_vswitch(self, switch: Union[List[str], str],
                    step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                    clobber: bool = False):
        '''Adds the command-line switch used to print the tool's version.

        This switch is passed to the executable to get its version string
        for checking.

        Args:
            switch (str): The version switch (e.g., '-v', '--version').
            clobber (bool): If True, overwrite existing values. Otherwise,
                append to them.

        Returns:
            The schema key that was set.
        '''
        if clobber:
            return self.set("vswitch", switch, step=step, index=index)
        else:
            return self.add("vswitch", switch, step=step, index=index)

    def add_licenseserver(self, name: str, server: str,
                          step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                          clobber: bool = False):
        '''Configures a license server connection for the tool.

        This sets the environment variables that commercial EDA tools use
        to find their license server.

        Args:
            name (str): The name of the license variable (e.g., 'LM_LICENSE_FILE').
            server (str): The server address (e.g., 'port@host').
            step (str, optional): The step associated with this setting.
                Defaults to the current step.
            index (str, optional): The index associated with this setting.
                Defaults to the current index.
            clobber (bool): If True, overwrite existing values. Otherwise,
                append to them.

        Returns:
            The schema key that was set.
        '''
        if clobber:
            return self.set("licenseserver", name, server, step=step, index=index)
        else:
            return self.add("licenseserver", name, server, step=step, index=index)

    def add_sbom(self, version: str, sbom: Union[str, List[str]], dataroot: Optional[str] = None,
                 step: Optional[str] = None, index: Optional[Union[str, int]] = None,
                 clobber: bool = False):
        '''Adds a Software Bill of Materials (SBOM) file for a tool version.

        Associates a specific tool version with its corresponding SBOM file,
        typically in SPDX or CycloneDX format.

        Args:
            version (str): The exact tool version this SBOM corresponds to.
            sbom (str): The path to the SBOM file.
            dataroot (str, optional): The data root this path is relative to.
                Defaults to the active package.
            clobber (bool): If True, overwrite existing values. Otherwise,
                append to them.

        Returns:
            The schema key that was set.
        '''
        with self.active_dataroot(self._get_active_dataroot(dataroot)):
            if clobber:
                return self.set("sbom", version, sbom, step=step, index=index)
            else:
                return self.add("sbom", version, sbom, step=step, index=index)

    def record_metric(self, metric: str, value: Union[int, float],
                      source_file: Optional[Union[List[Union[Path, str]], Path, str]] = None,
                      source_unit: Optional[str] = None,
                      quiet: bool = False):
        '''
        Records a metric and associates the source file with it.

        Args:
            metric (str): metric to record
            value (float/int): value of the metric that is being recorded
            source (str): file the value came from
            source_unit (str): unit of the value, if not provided it is assumed to have no units
            quiet (bool): dont generate warning on missing metric

        Examples:
            >>> self.record_metric('cellarea', 500.0, 'reports/metrics.json', \\
                    source_units='um^2')
            Records the metric cell area and notes the source as 'reports/metrics.json'
        '''

        if metric not in self.schema_metric.getkeys():
            if not quiet:
                self.logger.warning(f"{metric} is not a valid metric")
            return

        self.schema_metric.record(self.step, self.index, metric, value, unit=source_unit)
        if source_file:
            self.add("report", metric, source_file)

    def get_fileset_file_keys(self, filetype: str) -> List[Tuple[NamedSchema, Tuple[str, ...]]]:
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
        for obj, fileset in self.project.get_filesets():
            key = ("fileset", fileset, "file", filetype)
            if obj.valid(*key, check_complete=True):
                keys.append((obj, key))
        return keys

    ###############################################################
    # Schema
    ###############################################################
    def get(self, *keypath: str, field: Optional[str] = 'value',
            step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        if step is None:
            step = self.__step
        if index is None:
            index = self.__index
        return super().get(*keypath, field=field, step=step, index=index)

    def set(self, *args, field: str = 'value',
            step: Optional[str] = None, index: Optional[Union[str, int]] = None,
            clobber: bool = True):
        if step is None:
            step = self.__step
        if index is None:
            index = self.__index
        return super().set(*args, field=field, clobber=clobber, step=step, index=index)

    def add(self, *args, field: str = 'value',
            step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        if step is None:
            step = self.__step
        if index is None:
            index = self.__index
        return super().add(*args, field=field, step=step, index=index)

    def unset(self, *args: str,
              step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        if step is None:
            step = self.__step
        if index is None:
            index = self.__index
        return super().unset(*args, step=step, index=index)

    def find_files(self, *keypath: str, missing_ok: bool = False,
                   step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        if step is None:
            step = self.__step
        if index is None:
            index = self.__index
        return super().find_files(*keypath, missing_ok=missing_ok,
                                  step=step, index=index)

    @classmethod
    def find_task(cls: Type[TTask], project: "Project") -> Union[Set[TTask], TTask]:
        """Finds registered task(s) in a project that match the calling class.

        This method searches through all tasks configured in the provided `project`
        and returns those that meet specific criteria derived from the class on
        which this method is called. The filtering is based on three levels:

        1.  **Class Type**: The primary filter ensures that any found task object
            is an instance of the calling class (`cls`).
        2.  **Tool Name**: If the calling class (`cls`) implements the `tool()`
            method, the search is narrowed to tasks with that specific tool name.
        3.  **Task Name**: If the calling class (`cls`) implements the `task()`
            method, the search is further narrowed to tasks with that name.

        The method conveniently returns a single object if only one match is
        found, or a set of objects if multiple matches are found.

        Args:
            project (Project): The project instance to search within.

        Returns:
            Union[Task, Set[Task]]: A single Task instance if exactly one
            match is found, otherwise a set of matching Task instances.

        Raises:
            TypeError: If the `project` argument is not a valid `Project` object.
            ValueError: If no tasks matching the specified criteria are found in
                the project.
        """

        from siliconcompiler import Project
        if not isinstance(project, Project):
            raise TypeError("project must be a Project")

        task_obj: "Task" = cls()
        tool, task = None, None
        try:
            tool = task_obj.tool()
        except NotImplementedError:
            pass
        try:
            task = task_obj.task()
        except NotImplementedError:
            pass

        all_tasks: Set[Task] = set()
        for tool_name in project.getkeys("tool"):
            if tool and tool != tool_name:
                continue
            for task_name in project.getkeys("tool", tool_name, "task"):
                if task and task != task_name:
                    continue
                all_tasks.add(project.get("tool", tool_name, "task", task_name, field="schema"))

        tasks: Set[Task] = set()
        for task_obj in all_tasks:
            if not isinstance(task_obj, cls):
                continue
            tasks.add(task_obj)

        if not tasks:
            parts = []
            if tool:
                parts.append(f"tool='{tool}'")
            if task:
                parts.append(f"task='{task}'")
            parts.append(f"class={cls.__name__}")
            criteria = ", ".join(parts) if parts else "any criteria"
            raise ValueError(f"No tasks found matching {criteria}")

        if len(tasks) == 1:
            return next(iter(tasks))
        return tasks

    def _find_files_search_paths(self, key: str,
                                 step: Optional[str],
                                 index: Optional[Union[int, str]]) -> List[str]:
        search_paths = super()._find_files_search_paths(key, step, index)
        if key == "script":
            search_paths.extend(self.find_files("refdir", step=step, index=index))
        elif key == "input":
            search_paths.append(os.path.join(
                paths.workdir(self._parent(root=True), step=step, index=index), "inputs"))
        elif key == "report":
            search_paths.append(os.path.join(
                paths.workdir(self._parent(root=True), step=step, index=index), "reports"))
        elif key == "output":
            search_paths.append(os.path.join(
                paths.workdir(self._parent(root=True), step=step, index=index), "outputs"))
        return search_paths

    def _generate_doc(self, doc,
                      ref_root: str = "",
                      key_offset: Optional[Tuple[str, ...]] = None,
                      detailed: bool = True):
        from .schema.docs.utils import build_section, strong, KeyPath, code, para, \
            build_table, build_schema_value_table
        from docutils import nodes

        docs = []

        if not key_offset:
            key_offset = tuple()

        # Show dataroot
        dataroot = PathSchema._generate_doc(self, doc, ref_root=ref_root, key_offset=key_offset)
        if dataroot:
            docs.append(dataroot)

        # Show var definitions
        if self.valid("var"):
            table = [[strong('Parameters'), strong('Type'), strong('Help')]]
            for key in self.getkeys("var"):
                key_node = nodes.paragraph()
                with KeyPath.fallback(...):
                    key_node += KeyPath.keypath(
                        list(key_offset) + list(self._keypath) + ["var", key],
                        doc.env.docname,
                        key_text=["...", "var", key])

                param = self.get("var", key, field=None)
                help_str = param.get(field="help")

                val_type = param.get(field="type")
                if "<" in val_type:
                    encode_type = NodeType.parse(val_type)
                    try:
                        if val_type.startswith('['):
                            allowed = list(encode_type)[0].values
                            val_type = "[enum]"
                        elif val_type.startswith('{'):
                            allowed = list(encode_type)[0].values
                            val_type = "{enum}"
                        elif val_type.startswith('('):
                            allowed = []
                            val_type = val_type
                        else:
                            allowed = encode_type.values
                            val_type = "enum"
                    except:  # noqa E722
                        allowed = []
                        val_type = val_type

                    if allowed:
                        if help_str[-1] != ".":
                            help_str += "."
                        help_str = f"{help_str} Allowed values: {', '.join(sorted(allowed))}"

                table.append([
                    key_node,
                    code(val_type),
                    para(help_str)
                ])

            if len(table) > 1:
                vars = build_section("Variables", f"{ref_root}-variables")
                colspec = r'{|\X{2}{5}|\X{1}{5}|\X{2}{5}|}'
                vars += build_table(table, colspec=colspec)
                docs.append(vars)

        # Show tool information
        params = {}
        for key in self.allkeys(include_default=False):
            if key[0] == "dataroot":  # data root already handled
                continue
            params[key] = self.get(*key, field=None)

        with KeyPath.fallback(...):
            table = build_schema_value_table(params, "", list(key_offset) + list(self._keypath),
                                             trim_prefix=list(key_offset) + list(self._keypath))
        setup_info = build_section("Configuration", f"{ref_root}-config")
        setup_info += table
        docs.append(setup_info)

        return docs

    ###############################################################
    # Task methods
    ###############################################################
    @classmethod
    def make_docs(cls):
        from siliconcompiler import Flowgraph, Design, Project
        from siliconcompiler.scheduler import SchedulerNode
        design = Design("<design>")
        with design.active_fileset("docs"):
            design.set_topmodule("top")
        proj = Project(design)
        proj.add_fileset("docs")
        flow = Flowgraph("docsflow")
        flow.node("<step>", cls(), index="<index>")
        proj.set_flow(flow)

        node = SchedulerNode(proj, "<step>", "<index>")
        node.setup()
        return node.task

    def parse_version(self, stdout: str) -> str:
        """
        Parses the tool's version from its stdout. Must be implemented by subclasses.
        """
        raise NotImplementedError("must be implemented by the implementation class")

    def normalize_version(self, version: str) -> str:
        """
        Normalizes a version string to a standard format. Can be overridden.
        """
        return version

    def setup(self) -> None:
        """
        A hook for setting up the task before execution. Can be overridden.
        """
        pass

    def select_input_nodes(self) -> List[Tuple[str, str]]:
        """
        Determines which preceding nodes are inputs to this task.
        """
        return self.schema_flowruntime.get_node_inputs(
            self.step, self.index, record=self.schema_record)

    def pre_process(self) -> None:
        """
        A hook for pre-processing before the main tool execution. Can be overridden.
        """
        pass

    def runtime_options(self) -> List[Union[int, str, Path]]:
        """
        Constructs the default runtime options for the task. Can be extended.
        """
        cmdargs: List[Union[int, str, Path]] = []
        cmdargs.extend(self.get("option"))
        script: List[str] = self.find_files('script', missing_ok=True)
        if script:
            cmdargs.extend(script)
        return cmdargs

    def run(self) -> int:
        """
        The main execution logic for Python-based tasks. Must be implemented.
        """
        raise NotImplementedError("must be implemented by the implementation class")

    def post_process(self) -> None:
        """
        A hook for post-processing after the main tool execution. Can be overridden.
        """
        pass


class ShowTask(Task):
    """
    A specialized Task for tasks that display files (e.g., in a GUI viewer).

    This class provides a framework for dynamically finding and configuring
    viewer applications based on file types. It includes parameters for
    specifying the file to show and controlling the viewer's behavior.
    Subclasses should implement `get_supported_show_extentions` to declare
    which file types they can handle.
    """
    __TASKS_LOCK = threading.Lock()
    __TASKS = {}

    def __init__(self):
        """Initializes a ShowTask, adding specific parameters for show tasks."""
        super().__init__()
        self.add_parameter("showfilepath", "file", "path to show")
        self.add_parameter("showfiletype", "str", "filetype to show")
        self.add_parameter("shownode", "(str,str,str)",
                           "source node information, not always available")
        self.add_parameter("showexit", "bool", "exit after opening", defvalue=False)

    @classmethod
    def __check_task(cls, task: Optional[Type["ShowTask"]]) -> bool:
        """
        Private helper to validate if a task is a valid ShowTask or ScreenshotTask.
        """
        if cls is not ShowTask and cls is not ScreenshotTask:
            raise TypeError("class must be ShowTask or ScreenshotTask")

        if task is None:
            return False

        if cls is ShowTask:
            check, task_filter = ShowTask, ScreenshotTask
        else:
            check, task_filter = ScreenshotTask, None

        if not issubclass(task, check):
            return False
        if task_filter and issubclass(task, task_filter):
            return False

        return True

    @classmethod
    def register_task(cls, task: Optional[Type["ShowTask"]]) -> None:
        """
        Registers a new show task class for dynamic discovery.

        Args:
            task: The show task class to register.

        Raises:
            TypeError: If the task is not a valid subclass.
        """
        if not cls.__check_task(task):
            raise TypeError(f"task must be a subclass of {cls.__name__}")

        with cls.__TASKS_LOCK:
            cls.__TASKS.setdefault(cls, set()).add(task)

    @classmethod
    def __populate_tasks(cls) -> None:
        """
        Private helper to discover and populate all available show/screenshot tasks.

        This method recursively finds all subclasses and also loads tasks from
        any installed plugins.
        """
        cls.__check_task(None)

        def recurse(searchcls: Type["ShowTask"]):
            subclss = set()
            if not cls.__check_task(searchcls):
                return subclss

            subclss.add(searchcls)
            for subcls in searchcls.__subclasses__():
                subclss.update(recurse(subcls))

            return subclss

        classes = recurse(cls)

        # Support non-SC defined tasks from plugins
        for plugin in utils.get_plugins('showtask'):  # TODO rename
            plugin()

        if not classes:
            return

        with ShowTask.__TASKS_LOCK:
            ShowTask.__TASKS.setdefault(cls, set()).update(classes)

    @classmethod
    def get_task(cls, ext: Optional[str]) -> Union[Optional["ShowTask"], Set[Type["ShowTask"]]]:
        """
        Retrieves a suitable show task instance for a given file extension.

        Args:
            ext (str): The file extension to find a viewer for.

        Returns:
            An instance of a compatible ShowTask subclass, or None if
            no suitable task is found.
        """
        cls.__check_task(None)

        if cls not in ShowTask.__TASKS:
            cls.__populate_tasks()

        with ShowTask.__TASKS_LOCK:
            if cls not in ShowTask.__TASKS:
                return None
            tasks = ShowTask.__TASKS[cls].copy()

        # TODO: add user preference lookup (ext -> task)

        if ext is None:
            return tasks

        for task in tasks:
            try:
                if ext in task().get_supported_show_extentions():
                    return task()
            except NotImplementedError:
                pass

        return None

    def task(self) -> str:
        """Returns the name of this task."""
        return "show"

    def setup(self) -> None:
        """Sets up the parameters and requirements for the show task."""
        super().setup()

        self._set_filetype()

        self.add_required_key("var", "showexit")

        if self.get("var", "shownode"):
            self.add_required_key("var", "shownode")

        if self.get("var", "showfilepath"):
            self.add_required_key("var", "showfilepath")
        elif self.get("var", "showfiletype"):
            self.add_required_key("var", "showfiletype")
        else:
            raise ValueError("no file information provided to show")

    def get_supported_show_extentions(self) -> List[str]:
        """
        Returns a list of file extensions supported by this show task.
        This method must be implemented by subclasses.
        """
        raise NotImplementedError(
            "get_supported_show_extentions must be implemented by the child class")

    def _set_filetype(self) -> None:
        """
        Private helper to determine and set the 'showfiletype' parameter based
        on the provided 'showfilepath' or available input files.
        """
        def set_file(file, ext):
            if file.lower().endswith(".gz"):
                self.set("var", "showfiletype", f"{ext}.gz")
            else:
                self.set("var", "showfiletype", ext)

        if not self.get("var", "showfilepath"):
            exts = self.get_supported_show_extentions()

            if not self.get("var", "showfiletype"):
                input_files = {utils.get_file_ext(f): f.lower()
                               for f in self.get_files_from_input_nodes().keys()}
                for ext in exts:
                    if ext in input_files:
                        set_file(input_files[ext], ext)
                        break
            self.set("var", "showfiletype", exts[-1], clobber=False)
        else:
            file = self.get("var", "showfilepath")
            ext = utils.get_file_ext(file)
            set_file(file, ext)

    def set_showfilepath(self, path: str,
                         step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """Sets the path to the file to be displayed."""
        return self.set("var", "showfilepath", path, step=step, index=index)

    def set_showfiletype(self, file_type: str,
                         step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """Sets the type of the file to be displayed."""
        return self.set("var", "showfiletype", file_type, step=step, index=index)

    def set_showexit(self, value: bool,
                     step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """Sets whether the viewer application should exit after opening the file."""
        return self.set("var", "showexit", value, step=step, index=index)

    def set_shownode(self, jobname: Optional[str] = None,
                     nodestep: Optional[str] = None, nodeindex: Optional[Union[str, int]] = None,
                     step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """Sets the source node information for the file being displayed."""
        return self.set("var", "shownode", (jobname, nodestep, nodeindex), step=step, index=index)

    def get_tcl_variables(self, manifest: Optional[BaseSchema] = None) -> Dict[str, str]:
        """
        Gets Tcl variables for the task, ensuring 'sc_do_screenshot' is false
        for regular show tasks.
        """
        vars = super().get_tcl_variables(manifest)
        vars["sc_do_screenshot"] = "false"
        return vars


class ScreenshotTask(ShowTask):
    """
    A specialized Task for tasks that generate screenshots of files.

    This class inherits from `ShowTask` and is specifically for tasks
    that need to open a file, generate an image, and then exit. It automatically
    sets the 'showexit' parameter to True.
    """

    def task(self) -> str:
        """Returns the name of this task."""
        return "screenshot"

    def setup(self) -> None:
        """
        Sets up the screenshot task, ensuring that the viewer will exit
        after the screenshot is taken.
        """
        super().setup()
        # Ensure the viewer exits after taking the screenshot
        self.set_showexit(True)

    def get_tcl_variables(self, manifest: Optional[BaseSchema] = None) -> Dict[str, str]:
        """
        Gets Tcl variables for the task, setting 'sc_do_screenshot' to true.
        """
        vars = super().get_tcl_variables(manifest)
        vars["sc_do_screenshot"] = "true"
        return vars


def schema_task(schema):
    """
    Defines the standard parameters for a task within the schema.

    Args:
        schema (Schema): The schema object to add the parameters to.
    """
    schema = EditableSchema(schema)

    # Tool

    schema.insert(
        'exe',
        Parameter(
            'str',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Tool: executable name",
            switch="-tool_exe 'tool <str>'",
            example=["cli: -tool_exe 'openroad openroad'",
                     "api: task.set('tool', 'openroad', 'exe', 'openroad')"],
            help=trim("""Tool executable name.""")))

    schema.insert(
        'sbom', 'default',
        Parameter(
            '[file]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Tool: software BOM",
            switch="-tool_sbom 'tool version <file>'",
            example=[
                "cli: -tool_sbom 'yosys 1.0.1 ys_sbom.json'",
                "api: task.set('tool', 'yosys', 'sbom', '1.0', 'ys_sbom.json')"],
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
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Tool: executable path",
            switch="-tool_path 'tool <dir>'",
            example=[
                "cli: -tool_path 'openroad /usr/local/bin'",
                "api: task.set('tool', 'openroad', 'path', '/usr/local/bin')"],
            help=trim("""
            File system path to tool executable. The path is prepended to the
            system PATH environment variable for batch and interactive runs. The
            path parameter can be left blank if the :keypath:`tool,<tool>,task,<task>,exe` is
            already in the environment search path.""")))

    schema.insert(
        'vswitch',
        Parameter(
            '[str]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Tool: executable version switch",
            switch="-tool_vswitch 'tool <str>'",
            example=["cli: -tool_vswitch 'openroad -version'",
                     "api: task.set('tool', 'openroad', 'vswitch', '-version')"],
            help=trim("""
            Command line switch to use with executable used to print out
            the version number. Common switches include ``-v``, ``-version``,
            ``--version``. Some tools may require extra flags to run in batch mode.""")))

    schema.insert(
        'vendor',
        Parameter(
            'str',
            scope=Scope.JOB,
            shorthelp="Tool: vendor",
            switch="-tool_vendor 'tool <str>'",
            example=["cli: -tool_vendor 'yosys yosys'",
                     "api: task.set('tool', 'yosys', 'vendor', 'yosys')"],
            help=trim("""
            Name of the tool vendor. Parameter can be used to set vendor
            specific technology variables in the PDK and libraries. For
            open source projects, the project name should be used in
            place of vendor.""")))

    schema.insert(
        'version',
        Parameter(
            '[str]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Tool: version",
            switch="-tool_version 'tool <str>'",
            example=["cli: -tool_version 'openroad >=v2.0'",
                     "api: task.set('tool', 'openroad', 'version', '>=v2.0')"],
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
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Tool: file format",
            switch="-tool_format 'tool <str>'",
            example=["cli: -tool_format 'yosys tcl'",
                     "api: task.set('tool', 'yosys', 'format', 'tcl')"],
            help=trim("""
            File format for tool manifest handoff.""")))

    schema.insert(
        'licenseserver', 'default',
        Parameter(
            '[str]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="Tool: license servers",
            switch="-tool_licenseserver 'name key <str>'",
            example=[
                "cli: -tool_licenseserver 'atask ACME_LICENSE 1700@server'",
                "api: task.set('tool', 'acme', 'licenseserver', 'ACME_LICENSE', '1700@server')"],
            help=trim("""
            Defines a set of tool-specific environment variables used by the executable
            that depend on license key servers to control access. For multiple servers,
            separate servers with a colon. The named license variables are read at
            runtime (:meth:`.Task.run()`) and the environment variables are set.
            """)))

    # Task

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
                "api: task.set('tool', 'verilator', 'task', 'lint', 'warningoff', 'COMBDLY')"],
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
                "api: task.set('tool', 'openroad', 'task', 'place', 'regex', 'errors', "
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

                task.set('task', 'openroad', 'regex', 'place', '0', 'warnings',
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
                "api: task.set('tool', 'openroad', 'task', 'cts', 'option', '-no_init')"],
            help=trim("""
            List of command line options for the task executable, specified on
            a per task and per step basis. Options must not include spaces.
            For multiple argument options, each option is a separate list element.
            """)))

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
                "api: task.set('tool', 'openroad', 'task', 'cts', 'env', 'MYVAR', '42')"],
            help=trim("""
            Environment variables to set for individual tasks. Keys and values
            should be set in accordance with the task's documentation. Most
            tasks do not require extra environment variables to function.""")))

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
                "api: task.set('tool', 'openroad', 'task', 'place', 'input', 'oh_add.def', "
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
                "api: task.set('tool', 'openroad', 'task', 'place', 'output', 'oh_add.def', "
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
                     "api: task.set('tool', 'ghdl', 'task', 'import', 'stdout', 'destination', "
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
                     "api: task.set('tool', 'ghdl', 'task', 'import', 'stdout', 'suffix', 'log')"],
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
                     "api: task.set('tool', 'ghdl', 'task', 'import', 'stderr', 'destination', "
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
                     "api: task.set('tool', 'ghdl', 'task', 'import', 'stderr', 'suffix', 'log')"],
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
                "api: task.set('tool', 'openroad', 'task', 'cts', 'require', 'design')"],
            help=trim("""
            List of keypaths to required task parameters. The list is used
            by :meth:`.Project.check_manifest()` to verify that all parameters have been set up
            before step execution begins.""")))

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
                "api: task.set('tool', 'openroad', 'task', 'place', 'report', 'holdtns', "
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
                "api: task.set('tool', 'yosys', 'task', 'syn_asic', 'refdir', './myref')"],
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
                "api: task.set('tool', 'yosys', 'task', 'syn_asic', 'script', 'syn.tcl')"],
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
                "api: task.set('tool', 'yosys', 'task', 'syn_asic', 'prescript', 'syn_pre.tcl')"],
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
                "api: task.set('tool', 'yosys', 'task', 'syn_asic', 'postscript', 'syn_post.tcl')"],
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
                     "api: task.set('tool', 'magic', 'task', 'drc', 'threads', '64')"],
            help=trim("""
            Thread parallelism to use for execution specified on a per task and per
            step basis. If not specified, SC queries the operating system and sets
            the threads based on the maximum thread count supported by the
            hardware.""")))
