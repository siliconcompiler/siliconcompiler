import importlib
import inspect
import logging
import os
import shutil
import sys
import uuid

import os.path

from inspect import getfullargspec
from typing import Set, Union, List, Tuple, Type, Callable, TextIO

from siliconcompiler.schema import BaseSchema, NamedSchema, EditableSchema, Parameter
from siliconcompiler.schema.parametervalue import NodeListValue, NodeSetValue

from siliconcompiler import DesignSchema, LibrarySchema
from siliconcompiler import FlowgraphSchema
from siliconcompiler import RecordSchema
from siliconcompiler import MetricSchema
from siliconcompiler import ChecklistSchema
from siliconcompiler import ToolSchema, TaskSchema
from siliconcompiler import ShowTaskSchema, ScreenshotTaskSchema

from siliconcompiler.cmdlineschema import CommandLineSchema
from siliconcompiler.dependencyschema import DependencySchema
from siliconcompiler.pathschema import PathSchemaBase

from siliconcompiler.schema.schema_cfg import schema_option_runtime, schema_arg, schema_version

from siliconcompiler.report.dashboard.cli import CliDashboard
from siliconcompiler.scheduler import Scheduler
from siliconcompiler.utils.logging import SCColorLoggerFormatter, SCLoggerFormatter
from siliconcompiler.utils import FilterDirectories, get_file_ext


class Project(PathSchemaBase, CommandLineSchema, BaseSchema):
    """
    """

    def __init__(self, design: Union[DesignSchema, str] = None):
        super().__init__()

        # Initialize schema
        schema = EditableSchema(self)
        schema_version(schema)
        schema_arg(schema)

        schema.insert("checklist", "default", ChecklistSchema())
        schema.insert("library", "default", DesignSchema())
        schema.insert("flowgraph", "default", FlowgraphSchema())
        schema.insert("metric", MetricSchema())
        schema.insert("record", RecordSchema())
        schema.insert("tool", "default", ToolSchema())

        # Add options
        schema_option_runtime(schema)
        schema.insert("option", "env", "default", Parameter("str"))

        schema.insert("option", "design", Parameter("str", switch=["-design <str>"]))
        schema.insert("option", "alias", Parameter("[(str,str,str,str)]"))
        schema.insert("option", "fileset", Parameter("[str]"))

        # Add history
        schema.insert("history", BaseSchema())

        # Init logger
        self.__init_logger()

        # Init fields
        self.__cwd = os.getcwd()

        if design:
            if isinstance(design, str):
                self.set("option", "design", design)
            else:
                self.set_design(design)

        self.__dashboard = CliDashboard(self)

    def __init_logger(self):
        sc_logger = logging.getLogger("siliconcompiler")
        sc_logger.propagate = False
        self.__logger = sc_logger.getChild(f"project_{uuid.uuid4().hex}")
        self.__logger.propagate = False
        self.__logger.setLevel(logging.INFO)

        self._logger_console = logging.StreamHandler(stream=sys.stdout)
        if SCColorLoggerFormatter.supports_color(sys.stdout):
            self._logger_console.setFormatter(SCColorLoggerFormatter(SCLoggerFormatter()))
        else:
            self._logger_console.setFormatter(SCLoggerFormatter())

        self.__logger.addHandler(self._logger_console)

    @property
    def logger(self) -> logging.Logger:
        """
        Returns the logger for this project
        """
        return self.__logger

    @property
    def name(self) -> str:
        """
        Returns the name of the design
        """
        return self.get("option", "design")

    @property
    def design(self) -> DesignSchema:
        """
        Returns the design object
        """
        design_name = self.name
        if not design_name:
            raise ValueError("design name is not set")
        if not self.valid("library", design_name):
            raise KeyError(f"{design_name} design has not been loaded")

        return self.get("library", design_name, field="schema")

    @property
    def cwd(self) -> str:
        """
        Returns the working directory for the project
        """
        return self.__cwd

    @classmethod
    def convert(cls, obj: "Project") -> "Project":
        """
        Convert a project from one type to another

        Args:
            obj: Source object to convert from

        Returns:
            new object of the new class type
        """
        if not isinstance(obj, Project):
            raise TypeError("source object must be a Project")

        new_obj = cls()

        root_keys = new_obj.getkeys()
        import_keys = set(root_keys).intersection(obj.getkeys())

        if not issubclass(cls, obj.__class__):
            for rm in ("checklist", "flowgraph", "metric", "record", "tool", "schemaversion"):
                try:
                    import_keys.remove(rm)
                except KeyError:
                    pass

        manifest = obj.getdict()
        for key in list(manifest.keys()):
            if key not in import_keys:
                del manifest[key]

        new_obj._from_dict(manifest, [])

        return new_obj

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict
        """

        return Project.__name__

    def __populate_deps(self, obj: DependencySchema = None):
        """
        Ensure dependencies that are loaded contain pointers to the project
        libraries
        """
        if obj:
            obj._reset_deps()
        dep_map = {name: self.get("library", name, field="schema")
                   for name in self.getkeys("library")}
        for obj in dep_map.values():
            if isinstance(obj, DependencySchema):
                obj._populate_deps(dep_map)

    def _from_dict(self, manifest, keypath, version=None):
        ret = super()._from_dict(manifest, keypath, version)

        # Restore dependencies
        self.__populate_deps()

        return ret

    def load_target(self, target: Union[str, Callable[["Project"], None]], **kwargs):
        if isinstance(target, str):
            if "." not in target:
                raise ValueError("unable to process incomplete function path")

            *module, func = target.split(".")
            module = ".".join(module)

            mod = importlib.import_module(module)
            target = getattr(mod, func)

        func_spec = getfullargspec(target)

        args_len = len(func_spec.args or []) - len(func_spec.defaults or [])

        if args_len == 0 and not func_spec.args:
            raise ValueError('target signature cannot must take at least one argument')
        if args_len > 1:
            raise ValueError('target signature cannot have more than one required argument')

        proj_arg = func_spec.args[0]
        required_type = func_spec.annotations.get(proj_arg, Project)

        if not issubclass(required_type, Project):
            raise TypeError("target must take in a Project object")

        if not isinstance(self, required_type):
            raise TypeError(f"target requires a {required_type.__name__} project")

        target(self, **kwargs)

    def add_dep(self, obj):
        if isinstance(obj, (list, set, tuple)):
            for iobj in obj:
                self.add_dep(iobj)
            return

        if isinstance(obj, DesignSchema):
            if not self.has_library(obj.name):
                EditableSchema(self).insert("library", obj.name, obj)
        elif isinstance(obj, FlowgraphSchema):
            self.__import_flow(obj)
        elif isinstance(obj, LibrarySchema):
            if not self.has_library(obj.name):
                EditableSchema(self).insert("library", obj.name, obj)
        elif isinstance(obj, ChecklistSchema):
            if obj.name not in self.getkeys("checklist"):
                EditableSchema(self).insert("checklist", obj.name, obj)
        else:
            raise NotImplementedError

        # Copy dependencies into project
        if isinstance(obj, DependencySchema):
            for dep in obj.get_dep():
                self.add_dep(dep)

            # Rebuild dependencies to ensure instances are correct
            self.__populate_deps(obj)

    def __import_flow(self, flow: FlowgraphSchema):
        if flow.name in self.getkeys("flowgraph"):
            return

        edit_schema = EditableSchema(self)
        edit_schema.insert("flowgraph", flow.name, flow)

        # Instantiate tasks
        for task_cls in flow.get_all_tasks():
            task = task_cls()
            # TODO: this is not needed once tool moves
            if not self.valid("tool", task.tool()):
                edit_schema.insert("tool", task.tool(), ToolSchema())
            if not self.valid("tool", task.tool(), "task", task.task()):
                edit_schema.insert("tool", task.tool(), "task", task.task(), task)

    def check_manifest(self) -> bool:
        error = False

        # Assert design is set
        design = self.get("option", "design")
        if not design:
            self.logger.error("[option,design] has not been set")
            error = True
        else:
            # Assert design is a library
            if design not in self.getkeys("library"):
                self.logger.error(f"{design} has not been loaded")
                error = True

        # Assert fileset is set
        # Assert flow is set
        filesets = self.get("option", "fileset")
        if not filesets:
            self.logger.error("[option,fileset] has not been set")
            error = True
        elif design:
            # Assert fileset is in design
            design_obj = self.design
            for fileset in filesets:
                if fileset not in design_obj.getkeys("fileset"):
                    self.logger.error(f"{fileset} is not a valid fileset in {design}")
                    error = True

            # Assert design has topmodule
            fileset = filesets[0]
            if fileset in design_obj.getkeys("fileset"):
                if not design_obj.get_topmodule(fileset):
                    self.logger.error(f"topmodule has not been set in {design}/{fileset}")
                    error = True

        # Assert flow is set
        flow = self.get("option", "flow")
        if not flow:
            self.logger.error("[option,flow] has not been set")
            error = True
        else:
            if flow not in self.getkeys("flowgraph"):
                self.logger.error(f"{flow} has not need loaded")
                error = True

        # Check that alias libraries exist
        for src_lib, src_fileset, dst_lib, dst_fileset in self.get("option", "alias"):
            if not src_lib:
                self.logger.error("source library in [option,alias] must be set")
                error = True
                continue

            if src_lib not in self.getkeys("library"):
                continue

            if src_fileset not in self.getkeys("library", src_lib, "fileset"):
                self.logger.error(f"{src_fileset} is not a valid fileset in {src_lib}")
                error = True
                continue

            if not dst_lib:
                continue

            if dst_lib not in self.getkeys("library"):
                self.logger.error(f"{dst_lib} has not been loaded")
                error = True
                continue

            if dst_fileset and dst_fileset not in self.getkeys("library", dst_lib, "fileset"):
                self.logger.error(f"{dst_fileset} is not a valid fileset in {dst_lib}")
                error = True
                continue

        # Check flowgraph
        # Check tasks have classes, cannot check post setup that is a runtime check

        return not error

    def run(self, raise_exception=False):
        '''
        Executes tasks in a flowgraph.

        The run function sets up tools and launches runs for every node
        in the flowgraph starting with 'from' steps and ending at 'to' steps.
        From/to are taken from the schema from/to parameters if defined,
        otherwise from/to are defined as the entry/exit steps of the flowgraph.
        Before starting the process, tool modules are loaded and setup up for each
        step and index based on on the schema eda dictionary settings.
        Once the tools have been set up, the manifest is checked using the
        check_manifest() function and files in the manifest are hashed based
        on the 'hashmode' schema setting.

        Once launched, each process waits for preceding steps to complete,
        as defined by the flowgraph 'inputs' parameter. Once a all inputs
        are ready, previous steps are checked for errors before the
        process entered a local working directory and starts to run
        a tool or to execute a built in Chip function.

        Fatal errors within a step/index process cause all subsequent
        processes to exit before start, returning control to the the main
        program which can then exit.

        Args:
            raise_exception (bool): if True, will rethrow errors that the flow raises,
                otherwise will report the error and return False

        Examples:
            >>> run()
            Runs the execution flow defined by the flowgraph dictionary.
        '''
        from siliconcompiler.remote.client import ClientScheduler

        # Start dashboard
        if self.__dashboard and not self.__dashboard.is_running():
            self.__dashboard.open_dashboard()

        try:
            if self.get('option', 'remote'):
                scheduler = ClientScheduler(self)
            else:
                scheduler = Scheduler(self)
            scheduler.run()
        except Exception as e:
            if raise_exception:
                raise e
            self.logger.error(str(e))
            return False
        finally:
            if self.__dashboard:
                # Update dashboard
                self.__dashboard.update_manifest()
                self.__dashboard.end_of_run()

        return True

    def __getbuilddir(self) -> str:
        """
        Returns the path to the build directory
        """
        builddir = self.get('option', 'builddir')
        if os.path.isabs(builddir):
            return builddir

        return os.path.join(self.cwd, builddir)

    def getworkdir(self, step: str = None, index: Union[int, str] = None) -> str:
        """
        Returns absolute path to the work directory for a given step/index,
        if step/index not given, job directory is returned.

        Args:
            step (str): Node step name
            index (str/int): Node index
        """
        if not self.name:
            raise ValueError("name has not been set")

        dirlist = [self.__getbuilddir(),
                   self.name,
                   self.get('option', 'jobname')]

        # Return jobdirectory if no step defined
        # Return index 0 by default
        if step is not None:
            dirlist.append(step)

            if index is None:
                index = '0'

            dirlist.append(str(index))
        return os.path.join(*dirlist)

    def getcollectiondir(self):
        """
        Returns absolute path to collected files directory
        """
        return os.path.join(self.getworkdir(), "sc_collected_files")

    def collect(self,
                directory: str = None,
                verbose: bool = True,
                whitelist: List[str] = None):
        '''
        Collects files found in the configuration dictionary and places
        them in :meth:`.getcollectiondir`. The function only copies in files that have the 'copy'
        field set as true.

        Args:
            directory (filepath): Output filepath
            verbose (bool): Flag to indicate if logging should be used
            whitelist (list[path]): List of directories that are allowed to be
                collected. If a directory is is found that is not on this list
                a RuntimeError will be raised.
        '''

        if not directory:
            directory = self.getcollectiondir()
        directory = os.path.abspath(directory)

        # Remove existing directory
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory)

        if verbose:
            self.logger.info(f'Collecting files to: {directory}')

        dirs = {}
        files = {}

        for key in self.allkeys():
            if key[0] == 'history':
                # skip history
                continue

            # Skip runtime directories
            if key == ('option', 'builddir'):
                # skip builddir
                continue
            if key == ('option', 'cachedir'):
                # skip cache
                continue

            if key[0] == 'tool' and key[2] == 'task' and key[4] in ('input',
                                                                    'report',
                                                                    'output'):
                # skip flow files files from builds
                continue

            leaftype = self.get(*key, field='type')
            is_dir = "dir" in leaftype
            is_file = "file" in leaftype

            if not is_dir and not is_file:
                continue

            if not self.get(*key, field='copy'):
                continue

            for values, step, index in self.get(*key, field=None).getvalues(return_values=False):
                if not values.has_value:
                    continue

                if isinstance(values, (NodeSetValue, NodeListValue)):
                    values = values.values
                else:
                    values = [values]

                if is_dir:
                    dirs[(key, step, index)] = values
                else:
                    files[(key, step, index)] = values

        path_filter = FilterDirectories(self)
        for key, step, index in sorted(dirs.keys()):
            abs_paths = self.find_files(*key, step=step, index=index)

            new_paths = set()

            if not isinstance(abs_paths, (list, tuple, set)):
                abs_paths = [abs_paths]

            abs_paths = zip(abs_paths, dirs[(key, step, index)])
            abs_paths = sorted(abs_paths, key=lambda p: p[0])

            for abs_path, value in abs_paths:
                if not abs_path:
                    raise FileNotFoundError(f"{value.get()} could not be copied")

                if abs_path.startswith(directory):
                    # File already imported in directory
                    continue

                imported = False
                for new_path in new_paths:
                    if abs_path.startwith(new_path):
                        imported = True
                        break
                if imported:
                    continue

                new_paths.add(abs_path)

                import_path = os.path.join(directory, value.get_hashed_filename())
                if os.path.exists(import_path):
                    continue

                if whitelist is not None and abs_path not in whitelist:
                    raise RuntimeError(f'{abs_path} is not on the approved collection list.')

                if verbose:
                    self.logger.info(f"  Collecting directory: {abs_path}")
                path_filter.abspath = abs_path
                shutil.copytree(abs_path, import_path, ignore=path_filter.filter)
                path_filter.abspath = None

        for key, step, index in sorted(files.keys()):
            abs_paths = self.find_files(*key, step=step, index=index)

            if not isinstance(abs_paths, (list, tuple, set)):
                abs_paths = [abs_paths]

            abs_paths = zip(abs_paths, files[(key, step, index)])
            abs_paths = sorted(abs_paths, key=lambda p: p[0])

            for abs_path, value in abs_paths:
                if not abs_path:
                    raise FileNotFoundError(f"{value.get()} could not be copied")

                if abs_path.startswith(directory):
                    # File already imported in directory
                    continue

                import_path = os.path.join(directory, value.get_hashed_filename())
                if os.path.exists(import_path):
                    continue

                if verbose:
                    self.logger.info(f"  Collecting file: {abs_path}")
                shutil.copy2(abs_path, import_path)

    def history(self, job: str) -> "Project":
        '''
        Returns a *mutable* reference to ['history', job] as a Project object.

        Raises:
            KeyError: if job does not currently exist in history

        Args:
            job (str): Name of historical job to return.
        '''

        if job not in self.getkeys("history"):
            raise KeyError(f"{job} is not a valid job")

        return self.get("history", job, field="schema")

    def _record_history(self):
        '''
        Copies the current project into the history
        '''

        job = self.get("option", "jobname")
        proj = self.copy()

        # Remove history from proj
        EditableSchema(proj).insert("history", BaseSchema(), clobber=True)

        if job in self.getkeys("history"):
            self.logger.warning(f"Overwriting job {job}")

        EditableSchema(self).insert("history", job, proj, clobber=True)

    def __getstate__(self):
        # Ensure a copy of the state is used
        state = self.__dict__.copy()

        # Remove logger objects since they are not serializable
        del state["_Project__logger"]
        del state["_logger_console"]

        # Remove dashboard
        del state["_Project__dashboard"]

        return state

    def __setstate__(self, state):
        self.__dict__ = state

        # Reinitialize logger on restore
        self.__init_logger()

        # Restore dashboard
        self.__dashboard = CliDashboard(self)

    def get_filesets(self) -> List[Tuple[NamedSchema, str]]:
        """
        Returns the filesets selected for this project
        """
        # Build alias mapping
        alias = {}
        for src_lib, src_fileset, dst_lib, dst_fileset in self.get("option", "alias"):
            if dst_lib:
                if not self.valid("library", dst_lib):
                    raise KeyError(f"{dst_lib} is not a loaded library")
                dst_obj = self.get("library", dst_lib, field="schema")
            else:
                dst_obj = None
            if not dst_fileset:
                dst_fileset = None
            alias[(src_lib, src_fileset)] = (dst_obj, dst_fileset)

        return self.design.get_fileset(self.get("option", "fileset"), alias=alias)

    def get_task(self,
                 tool: str = None,
                 task: str = None,
                 filter: Union[Type[TaskSchema], Callable[[TaskSchema], bool]] = None) -> \
            Union[Set[TaskSchema], TaskSchema]:
        """Retrieves tasks based on specified criteria.

        This method allows you to fetch tasks by tool name, task name, or by applying a custom
        filter. If a single task matches the criteria, that task object is returned directly.
        If multiple tasks match, a set of :class:`TaskSchema` objects is returned.
        If no criteria are provided, all available tasks are returned.

        Args:
            tool (str, optional): The name of the tool to filter tasks by. Defaults to None.
            task (str, optional): The name of the task to filter by. Defaults to None.
            filter (Union[Type[TaskSchema], Callable[[TaskSchema], bool]], optional):
                A filter to apply to the tasks. This can be:
                - A `Type[TaskSchema]`: Only tasks that are instances of this type will be returned.
                - A `Callable[[TaskSchema], bool]`: A function that takes a `TaskSchema` object
                and returns `True` if the task should be included, `False` otherwise.
                Defaults to None.

        Returns:
            Union[Set[TaskSchema], TaskSchema]:
                - If exactly one task matches the criteria, returns that single `TaskSchema` object.
                - If multiple tasks match or no specific tool/task is provided (and thus all tasks
                are considered), returns a `Set[TaskSchema]` containing the matching tasks.
        """
        all_tasks: Set[TaskSchema] = set()
        for tool_name in self.getkeys("tool"):
            for task_name in self.getkeys("tool", tool_name, "task"):
                all_tasks.add(self.get("tool", tool_name, "task", task_name, field="schema"))

        tasks = set()
        for task_obj in all_tasks:
            if tool and task_obj.tool() != tool:
                continue
            if task and task_obj.task() != task:
                continue
            if filter:
                if inspect.isclass(filter):
                    if not isinstance(task_obj, filter):
                        continue
                elif callable(filter):
                    if not filter(task_obj):
                        continue
            tasks.add(task_obj)

        if len(tasks) == 1:
            return list(tasks)[0]
        return tasks

    def set_design(self, design: Union[DesignSchema, str]):
        """
        Set the design for this project

        Args:
            design (:class:`DesignSchema` or str): design object or name
        """
        if isinstance(design, DesignSchema):
            self.add_dep(design)
            design = design.name
        elif not isinstance(design, str):
            raise TypeError("design must be string or Design object")

        return self.set("option", "design", design)

    def set_flow(self, flow: Union[FlowgraphSchema, str]):
        """
        Set the flow for this project

        Args:
            design (:class:`FlowgraphSchema` or str): flow object or name
        """
        if isinstance(flow, FlowgraphSchema):
            self.add_dep(flow)
            flow = flow.name
        elif not isinstance(flow, str):
            raise TypeError("flow must be string or Flowgraph object")

        return self.set("option", "flow", flow)

    def add_fileset(self, fileset: Union[List[str], str], clobber: bool = False):
        """
        Add a fileset to use in this project

        Args:
            fileset (list of str): name of fileset from the design
            clobber (bool): if True, replace the filesets
        """
        if not isinstance(fileset, str):
            if isinstance(fileset, (list, tuple, set)):
                if not all([isinstance(v, str) for v in fileset]):
                    raise TypeError("fileset must be a string")
            else:
                raise TypeError("fileset must be a string")

        if isinstance(fileset, str):
            fileset = [fileset]

        for fs in fileset:
            if not self.design.has_fileset(fs):
                raise ValueError(f"{fs} is not a valid fileset in {self.design.name}")

        if clobber:
            return self.set("option", "fileset", fileset)
        else:
            return self.add("option", "fileset", fileset)

    def add_alias(self,
                  src_dep: Union[DesignSchema, str],
                  src_fileset: str,
                  alias_dep: Union[DesignSchema, str],
                  alias_fileset: str,
                  clobber: bool = False):
        """
        Add an aliased fileset.

        Args:
            src_dep (:class:`DesignSchema` or str): source design to alias
            src_fileset (str): source fileset to alias
            alias_dep (:class:`DesignSchema` or str): replacement design
            alias_fileset (str): replacement fileset
            clobber (bool): overwrite existing values
        """

        if isinstance(src_dep, str):
            if self.has_library(src_dep):
                src_dep = self.get("library", src_dep, field="schema")
            else:
                src_dep_name = src_dep
                src_dep = None

        if src_dep is not None:
            if isinstance(src_dep, DesignSchema):
                src_dep_name = src_dep.name
                if not self.has_library(src_dep_name):
                    self.add_dep(src_dep)
            else:
                raise TypeError("source dep is not a valid type")

            if not src_dep.has_fileset(src_fileset):
                raise ValueError(f"{src_dep_name} does not have {src_fileset} as a fileset")

        if alias_dep is None:
            alias_dep = ""

        if alias_fileset == "":
            alias_fileset = None

        if isinstance(alias_dep, str):
            if alias_dep == "":
                alias_dep = None
                alias_dep_name = None
                alias_fileset = None
            else:
                if not self.has_library(alias_dep):
                    raise KeyError(f"{alias_dep} has not been loaded")

                alias_dep = self.get("library", alias_dep, field="schema")

        if alias_dep is not None:
            if isinstance(alias_dep, DesignSchema):
                alias_dep_name = alias_dep.name
                if not self.has_library(alias_dep_name):
                    self.add_dep(alias_dep)
            else:
                raise TypeError("alias dep is not a valid type")

            if alias_fileset is not None and not alias_dep.has_fileset(alias_fileset):
                raise ValueError(f"{alias_dep_name} does not have {alias_fileset} as a fileset")

        alias = (src_dep_name, src_fileset, alias_dep_name, alias_fileset)
        if clobber:
            return self.set("option", "alias", alias)
        else:
            return self.add("option", "alias", alias)

    def has_library(self, library: str) -> bool:
        """
        Returns true if the library exists
        """

        if isinstance(library, NamedSchema):
            library = library.name

        return library in self.getkeys("library")

    def _summary_headers(self) -> List[Tuple[str, str]]:
        """
        Project defined headers to add to summary.
        If projects require additional information they can extend this
        method to add additional information.
        """

        alias = []
        for src, src_fs, dst, dst_fs in self.get("option", "alias"):
            if not self.has_library(src):
                continue
            if dst and not self.has_library(dst):
                continue

            aliased = f"{src} ({src_fs}) -> "
            if not dst:
                aliased += "deleted"
            elif not dst_fs:
                aliased += "deleted"
            else:
                aliased += f"{dst} ({dst_fs})"
            alias.append(aliased)

        filesets = self.get("option", "fileset")

        headers = [
            ("design", self.get("option", "design"))
        ]
        if filesets:
            headers.append(("filesets", ", ".join(filesets)))
        if alias:
            headers.append(("alias", ", ".join(alias)))
        headers.append(("jobdir", self.getworkdir()))

        return headers

    def _snapshot_info(self) -> List[Tuple[str, str]]:
        """
        Project defined information to add to snapshots.
        If projects require additional information they can extend this
        method to add additional information.
        """

        info = [
            ("Design", self.get("option", "design"))
        ]

        return info

    def summary(self, jobname: str = None, fd: TextIO = None) -> None:
        '''
        Prints a summary of the compilation manifest.

        Metrics from the flowgraph nodes, or from/to parameter if
        defined, are printed out on a per step basis.

        Args:
            jobname (str): If provided prints uses this job to print summary,
                otherwise the value in :keypath:`option,jobname` will be used.
            fd (TextIO): If provided prints to this file descriptor instead of stdout.

        Examples:
            >>> chip.summary()
            Prints out a summary of the run to stdout.
        '''
        histories = self.getkeys("history")

        if not histories:
            raise ValueError("no history to summarize")

        if jobname is None:
            jobname = self.get("option", "jobname")
        if jobname not in histories:
            org_job = jobname
            jobname = histories[0]
            self.logger.warning(f"{org_job} not found in history, picking {jobname}")

        history = self.history(jobname)
        history.get("metric", field='schema').summary(
            headers=history._summary_headers(),
            fd=fd)

    def find_result(self,
                    filetype: str = None, step: str = None,
                    index: str = "0", directory: str = "outputs",
                    filename: str = None) -> str:
        """
        Returns the absolute path of a compilation result.
        Utility function that returns the absolute path to a results
        file based on the provided arguments. The result directory
        structure is:
        <dir>/<design>/<jobname>/<step>/<index>/<directory>/<design>.<filetype>
        Args:
            filetype (str): File extension (v, def, etc)
            step (str): Task step name ('syn', 'place', etc)
            jobname (str): Jobid directory name
            index (str): Task index
            directory (str): Node directory to search
            filename (str): exact filename to search for
        Returns:
            Returns absolute path to file or None is the file is not found
        Examples:
            >>> vg_filepath = chip.find_result('vg', 'syn')
           Returns the absolute path to the gate level verilog.
        """

        if filename and step is None:
            step = filetype

        if step is None:
            raise ValueError("step is required")

        workdir = self.getworkdir(step, index)

        if not filename:
            fileset = self.get("option", "fileset")
            if not fileset:
                raise ValueError("[option,fileset] is not set")
            design_name = self.design.get_topmodule(fileset[0])

            checkfiles = [
                os.path.join(workdir, directory, f'{design_name}.{filetype}'),
                os.path.join(workdir, directory, f'{design_name}.{filetype}.gz')
            ]
        else:
            checkfiles = [
                os.path.join(workdir, directory, filename)
            ]

        for filename in checkfiles:
            self.logger.debug(f"Finding node file: {filename}")
            if os.path.exists(filename):
                return os.path.abspath(filename)

        return None

    def snapshot(self, path: str = None, display: bool = True) -> None:
        '''
        Creates a snapshot image of the job
        Args:
            path (str): Path to generate the image at, if not provided will default to
                <job>/<design>.png
            display (bool): If True, will open the image for viewing. If :keypath:`option,nodisplay`
                is True, this argument will be ignored.
        Examples:
            >>> chip.snapshot()
            Creates a snapshot image in the default location
        '''
        from siliconcompiler.report import generate_summary_image, _open_summary_image

        if not path:
            path = os.path.join(self.getworkdir(), f'{self.design.name}.png')

        if os.path.exists(path):
            os.remove(path)

        generate_summary_image(self, path, self._snapshot_info())

        if os.path.isfile(path) and not self.get('option', 'nodisplay') and display:
            _open_summary_image(path)

    def show(self, filename=None, screenshot=False, extension=None) -> str:
        '''
        Opens a graphical viewer for the filename provided.
        The show function opens the filename specified using a viewer tool
        selected based on the file suffix and the registered showtools.
        Display settings and technology settings for viewing the file are read
        from the in-memory chip object schema settings. All temporary render
        and display files are saved in the <build_dir>/_show_<jobname> directory.
        Args:
            filename (path): Name of file to display
            screenshot (bool): Flag to indicate if this is a screenshot or show
            extension (str): extension of file to show
        Examples:
            >>> show('build/oh_add/job0/write.gds/0/outputs/oh_add.gds')
            Displays gds file with a viewer assigned by showtool
        '''

        tool_cls = ScreenshotTaskSchema if screenshot else ShowTaskSchema

        sc_jobname = self.get("option", "jobname")
        sc_step = None
        sc_index = None

        has_filename = filename is not None
        # Finding last layout if no argument specified
        if filename is None:
            try:
                search_obj = self.history(sc_jobname)
            except KeyError:
                search_obj = self

            self.logger.info('Searching build directory for layout to show.')

            search_nodes = []
            flow = search_obj.get("option", "flow")
            if flow:
                flow_obj = search_obj.get("flowgraph", flow, field="schema")
                for nodes in flow_obj.get_execution_order(reverse=True):
                    search_nodes.extend(nodes)

            exts = set()
            for cls in tool_cls.get_task(None):
                try:
                    exts.update(cls().get_supported_show_extentions())
                except NotImplementedError:
                    pass

            for ext in exts:
                if extension and extension != ext:
                    continue

                for step, index in search_nodes:
                    filename = search_obj.find_result(ext,
                                                      step=step,
                                                      index=index)
                    if filename:
                        sc_step = step
                        sc_index = index
                        break
                if filename:
                    break

        if filename is None:
            self.logger.error('Unable to automatically find layout in build directory.')
            self.logger.error('Try passing in a full path to show() instead.')
            return

        filepath = os.path.abspath(filename)

        if not has_filename:
            self.logger.info(f'Showing file {filename}')

        # Check that file exists
        if not os.path.exists(filepath):
            self.logger.error(f"Invalid filepath {filepath}.")
            return

        filetype = get_file_ext(filepath)

        task = tool_cls.get_task(filetype)
        if task is None:
            self.logger.error(f"Filetype '{filetype}' not available in the registered showtools.")
            return False

        # Create copy of project to avoid changing user project
        proj = self.copy()

        nodename = "screenshot" if screenshot else "show"

        class ShowFlow(FlowgraphSchema):
            """
            Small auto created flow to build a single node show/screenshot flow
            """
            def __init__(self, nodename, task):
                super().__init__()
                self.set_name("showflow")

                self.node(nodename, task)

        proj.set_flow(ShowFlow(nodename, task))

        # Setup options:
        for option, value in [
                ("track", False),
                ("hash", False),
                ("nodisplay", False),
                ("continue", True),
                ("quiet", False),
                ("clean", True)]:
            proj.set("option", option, value)
        proj.unset("arg", "step")
        proj.unset("arg", "index")
        proj.unset("option", "to")
        proj.unset("option", "prune")
        proj.unset("option", "from")

        jobname = f"_{nodename}_{sc_jobname}_{sc_step}_{sc_index}_{task.tool()}"
        proj.set("option", "jobname", jobname)

        # Setup in task variables
        task: ShowTaskSchema = proj.get_task(filter=task.__class__)
        task.set_showfilepath(filename)
        task.set_showfiletype(filetype)
        task.set_shownode(jobname=sc_jobname, step=sc_step, index=sc_index)

        # run show flow
        proj.run(raise_exception=True)
        if screenshot:
            return proj.find_result('png', step=nodename)
