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

from siliconcompiler.schema import BaseSchema, NamedSchema, EditableSchema, Parameter, Scope
from siliconcompiler.schema.parametervalue import NodeListValue, NodeSetValue
from siliconcompiler.schema.utils import trim

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
    The Project class is the core object in SiliconCompiler, representing a
    complete hardware design project. It manages design parameters, libraries,
    flowgraphs, metrics, and provides methods for compilation, data collection,
    and reporting.
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
        schema.insert(
            "option", "env", "default",
            Parameter(
                "str",
                scope=Scope.GLOBAL,
                shorthelp="Option: environment variables",
                example=["api: project.set('option', 'env', 'PDK_HOME', '/disk/mypdk')"],
                help=trim("""
                    Certain tools and reference flows require global environment
                    variables to be set. These variables can be managed externally or
                    specified through the env variable.""")))

        schema.insert(
            "option", "design",
            Parameter(
                "str",
                scope=Scope.GLOBAL,
                shorthelp="Option: Design library name",
                example=["cli: -design hello_world",
                         "api: project.set('option', 'design', 'hello_world')"],
                switch=["-design <str>"],
                help="Name of the top level library"))
        schema.insert(
            "option", "alias",
            Parameter(
                "[(str,str,str,str)]",
                scope=Scope.GLOBAL,
                shorthelp="Option: Fileset alias mapping",
                example=["api: project.set('option', 'alias', ('design', 'rtl', 'lambda', 'rtl')"],
                help=trim("""List of filesets to alias during a run. When an alias is specific
                    it will be used instead of the source fileset. It is useful when you
                    want to substitute a fileset from one library with a fileset from another,
                    without changing the original design's code.
                    For example, you might use it to swap in a different version of an IP
                    block or a specific test environment.""")))
        schema.insert(
            "option", "fileset",
            Parameter(
                "[str]",
                scope=Scope.GLOBAL,
                shorthelp="Option: Selected design filesets",
                example=["api: project.set('option', 'fileset', 'rtl')"],
                help=trim("""List of filesets to use from the selected design library""")))

        schema.insert(
            "option", "nodashboard",
            Parameter(
                "bool",
                defvalue=False,
                scope=Scope.GLOBAL,
                switch=["-nodashboard <bool>"],
                shorthelp="Option: Disables the dashboard",
                example=["api: project.set('option', 'nodashboard', True)"],
                help=trim("""Disables the dashboard during execution""")))

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

        self.__init_dashboard()

    def __init_logger(self):
        """
        Initializes the project-specific logger.
        """
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

    def __init_dashboard(self):
        """
        Initializes or disables the CLI dashboard for the project.

        If the 'nodashboard' option is set to True, any existing dashboard
        instance is stopped and set to None. Otherwise, a new `CliDashboard`
        instance is created and assigned to the project.
        """
        if self.get("option", "nodashboard"):
            try:
                if self.__dashboard:
                    self.__dashboard.stop()
            except AttributeError:
                pass
            self.__dashboard = None
        else:
            self.__dashboard = CliDashboard(self)

    def set(self, *args, field='value', clobber=True, step=None, index=None):
        ret = super().set(*args, field=field, clobber=clobber, step=step, index=index)

        # Special handling keys
        if args[0:2] == ("option", "nodashboard"):
            self.__init_dashboard()

        return ret

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
        Ensures that all loaded dependencies (like libraries) within the project
        contain correct internal pointers back to the project's libraries.
        This is crucial for maintaining a consistent and navigable schema graph.

        Args:
            obj (DependencySchema, optional): An optional dependency object to
                reset and populate. If None, all existing library dependencies
                in the project are processed. Defaults to None.
        """
        if obj:
            obj._reset_deps()
        dep_map = {name: self.get("library", name, field="schema")
                   for name in self.getkeys("library")}
        for obj in dep_map.values():
            if isinstance(obj, DependencySchema):
                obj._populate_deps(dep_map)

    def _from_dict(self, manifest, keypath, version=None):
        """
        Populates the project's schema from a dictionary representation.

        This method is typically used during deserialization or when loading
        a project state from a manifest. After loading the data, it ensures
        that internal dependencies are correctly re-established.

        Args:
            manifest (dict): The dictionary containing the schema data.
            keypath (list): The current keypath being processed (used internally
                            for recursive loading).
            version (str, optional): The schema version of the manifest. Defaults to None.

        Returns:
            Any: The result of the superclass's `_from_dict` method.
        """
        ret = super()._from_dict(manifest, keypath, version)

        # Restore dependencies
        self.__populate_deps()

        return ret

    def load_target(self, target: Union[str, Callable[["Project"], None]], **kwargs):
        """
        Loads and executes a target function or method within the project context.

        This method allows dynamically loading a Python function (e.g., a target
        defined in a separate module) and executing it. It performs type checking
        to ensure the target function accepts a Project object as its first
        required argument and that the current project instance is compatible
        with the target's expected Project type.

        Args:
            target (Union[str, Callable[["Project"], None]]):
                The target to load. This can be:
                - A string in the format "module.submodule.function_name"
                - A callable Python function that accepts a Project object as its
                  first argument.
            **kwargs: Arbitrary keyword arguments to pass to the target function.

        Raises:
            ValueError: If the target string path is incomplete, if the target
                        signature does not meet the requirements (e.g., no
                        required arguments, or more than one required argument).
            TypeError: If the target does not take a Project object as its
                       first argument, or if the current project instance is
                       not compatible with the target's required Project type.
        """
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
        """
        Adds a dependency object (e.g., a DesignSchema, FlowgraphSchema, LibrarySchema,
        or ChecklistSchema) to the project.

        This method intelligently adds various types of schema objects to the
        project's internal structure. It also handles recursive addition of
        dependencies if the added object itself is a `DependencySchema`.

        Args:
            obj (Union[DesignSchema, FlowgraphSchema, LibrarySchema, ChecklistSchema,
                       List, Set, Tuple]):
                The dependency object(s) to add. Can be a single schema object
                or a collection (list, set, tuple) of schema objects.

        Raises:
            NotImplementedError: If the type of the object is not supported.
        """
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
        self._import_dep(obj)

    def _import_dep(self, obj: DependencySchema):
        # Copy dependencies into project
        if isinstance(obj, DependencySchema):
            for dep in obj.get_dep():
                self.add_dep(dep)

            # Rebuild dependencies to ensure instances are correct
            self.__populate_deps(obj)

    def __import_flow(self, flow: FlowgraphSchema):
        """
        Imports a FlowgraphSchema into the project.

        If the flowgraph with the given name is not already present, it is
        added to the project's flowgraph schema. This method also instantiates
        and registers all tasks defined within the imported flowgraph, ensuring
        that the necessary tool and task schemas are available.

        Args:
            flow (FlowgraphSchema): The flowgraph schema object to import.
        """
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
        """
        Performs a comprehensive check of the project's manifest (configuration)
        for consistency and validity.

        This method verifies that essential options like 'design', 'fileset',
        and 'flow' are properly set. It also checks if the specified design
        and flowgraph are loaded, and if filesets within the selected design
        are valid and have a top module defined. Additionally, it validates
        any defined fileset aliases, ensuring that source and destination
        libraries and filesets exist. Error messages are logged for any
        detected inconsistencies.

        Returns:
            bool: True if the manifest is valid and all checks pass, False otherwise.
        """
        error = False

        # Assert design is set
        design = self.get("option", "design")
        if not design:
            self.logger.error("[option,design] has not been set")
            error = True
        else:
            # Assert design is a library
            if not self.has_library(design):
                self.logger.error(f"{design} has not been loaded")
                error = True

        # Assert fileset is set
        filesets = self.get("option", "fileset")
        if not filesets:
            self.logger.error("[option,fileset] has not been set")
            error = True
        elif design:  # Only check fileset in design if design is valid
            # Assert fileset is in design
            design_obj = self.design  # This is a mock object
            for fileset in filesets:
                if not design_obj.has_fileset(fileset):
                    self.logger.error(f"{fileset} is not a valid fileset in {design}")
                    error = True

            # Assert design has topmodule
            # This check only happens if filesets are provided and design is valid
            if filesets and design_obj.has_fileset(filesets[0]):
                if not design_obj.get_topmodule(filesets[0]):
                    self.logger.error(f"topmodule has not been set in {design}/{filesets[0]}")
                    error = True

        # Assert flow is set
        flow = self.get("option", "flow")
        if not flow:
            self.logger.error("[option,flow] has not been set")
            error = True
        else:
            if flow not in self.getkeys("flowgraph"):
                self.logger.error(f"{flow} has not been loaded")
                error = True

        # Check that alias libraries exist
        # Default to an empty list if 'alias' is not set, to avoid TypeError
        aliases = self.get("option", "alias") or []
        for src_lib, src_fileset, dst_lib, dst_fileset in aliases:
            if not src_lib:
                self.logger.error("source library in [option,alias] must be set")
                error = True
                continue

            # If src_lib is not in getkeys("library"), skip further checks for this alias
            # as the error would have been caught earlier if it was a 'design' check.
            # This path is for aliases where src_lib itself might not be a primary design.
            if not self.has_library(src_lib):
                continue

            if not self.get("library", src_lib, field="schema").has_fileset(src_fileset):
                self.logger.error(f"{src_fileset} is not a valid fileset in {src_lib}")
                error = True
                continue

            if not dst_lib:
                continue

            if not self.has_library(dst_lib):
                self.logger.error(f"{dst_lib} has not been loaded")
                error = True
                continue

            if dst_fileset and \
                    not self.get("library", dst_lib, field="schema").has_fileset(dst_fileset):
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
        from siliconcompiler.remote import ClientScheduler

        # Start dashboard
        if self.__dashboard:
            if not self.__dashboard.is_running():
                self.__dashboard.open_dashboard()
            # Attach logger
            self.__dashboard.set_logger(self.logger)

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
        Returns the absolute path to the project's build directory.

        This directory is where all intermediate and final compilation
        artifacts are stored.

        Returns:
            str: The absolute path to the build directory.
        """
        builddir = self.get('option', 'builddir')
        if os.path.isabs(builddir):
            return builddir

        return os.path.join(self.cwd, builddir)

    def getworkdir(self, step: str = None, index: Union[int, str] = None) -> str:
        """
        Returns the absolute path to the working directory for a given
        step and index within the project's job structure.

        The directory structure is typically:
        `<build_dir>/<design_name>/<job_name>/<step>/<index>/`

        If `step` and `index` are not provided, the job directory is returned.
        If `step` is provided but `index` is not, index '0' is assumed.

        Args:
            step (str, optional): The name of the flowgraph step (e.g., 'syn', 'place').
                                  Defaults to None.
            index (Union[int, str], optional): The index of the task within the step.
                                               Defaults to None (implies '0' if step is set).

        Returns:
            str: The absolute path to the specified working directory.

        Raises:
            ValueError: If the design name is not set in the project.
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
        Returns the absolute path to the directory where collected files are stored.

        This directory is typically located within the project's working directory
        and is used to consolidate files marked for collection.

        Returns:
            str: The absolute path to the collected files directory.
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
        self.__init_dashboard()

    def get_filesets(self) -> List[Tuple[NamedSchema, str]]:
        """
        Returns the filesets selected for this project
        """
        # Build alias mapping
        alias = {}
        for src_lib, src_fileset, dst_lib, dst_fileset in self.get("option", "alias"):
            if dst_lib:
                if not self.has_library(dst_lib):
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
        Sets the active design for this project.

        This method allows you to specify the primary design that the project
        will operate on. If a `DesignSchema` object is provided, it is first
        added as a dependency.

        Args:
            design (Union[DesignSchema, str]): The design object or its name (string)
                                               to be set as the current design.

        Raises:
            TypeError: If the provided `design` is not a string or a `DesignSchema` object.
        """
        if isinstance(design, DesignSchema):
            self.add_dep(design)
            design = design.name
        elif not isinstance(design, str):
            raise TypeError("design must be string or Design object")

        return self.set("option", "design", design)

    def set_flow(self, flow: Union[FlowgraphSchema, str]):
        """
        Sets the active flowgraph for this project.

        This method allows you to specify the sequence of steps and tasks
        (the flow) that the project will execute. If a `FlowgraphSchema` object
        is provided, it is first added as a dependency.

        Args:
            flow (Union[FlowgraphSchema, str]): The flowgraph object or its name (string)
                                                to be set as the current flow.

        Raises:
            TypeError: If the provided `flow` is not a string or a `FlowgraphSchema` object.
        """
        if isinstance(flow, FlowgraphSchema):
            self.add_dep(flow)
            flow = flow.name
        elif not isinstance(flow, str):
            raise TypeError("flow must be string or Flowgraph object")

        return self.set("option", "flow", flow)

    def add_fileset(self, fileset: Union[List[str], str], clobber: bool = False):
        """
        Adds one or more filesets to be used in this project.

        Filesets are collections of related files within a design. This method
        allows you to specify which filesets from the selected design library
        should be included in the current project context.

        Args:
            fileset (Union[List[str], str]): The name(s) of the fileset(s) to add.
                                             Can be a single string or a list of strings.
            clobber (bool): If True, existing filesets will be replaced by the new ones.
                            If False, new filesets will be added to the existing list.
                            Defaults to False.

        Raises:
            TypeError: If `fileset` is not a string or a list/tuple/set of strings.
            ValueError: If any of the specified filesets are not found in the currently
                        selected design.
        """
        if not isinstance(fileset, str):
            if isinstance(fileset, (list, tuple, set)):
                if not all([isinstance(v, str) for v in fileset]):
                    raise TypeError("fileset must be a string or a list/tuple/set of strings")
            else:
                raise TypeError("fileset must be a string or a list/tuple/set of strings")

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
        Adds an aliased fileset mapping to the project.

        This method allows you to redirect a fileset reference from a source
        library/fileset to a different destination library/fileset. This is
        useful for substituting design components or test environments without
        modifying the original design.

        Args:
            src_dep (Union[DesignSchema, str]): The source design library (object or name)
                                                from which the fileset is being aliased.
            src_fileset (str): The name of the source fileset to alias.
            alias_dep (Union[DesignSchema, str]): The destination design library (object or name)
                                                  to which the fileset is being redirected.
                                                  Can be None or an empty string to indicate
                                                  deletion.
            alias_fileset (str): The name of the destination fileset. Can be None or an empty string
                                 to indicate deletion of the fileset reference.
            clobber (bool): If True, any existing alias for `(src_dep, src_fileset)` will be
                            overwritten. If False, the alias will be added (or updated if it's
                            the same source). Defaults to False.

        Raises:
            TypeError: If `src_dep` or `alias_dep` are not valid types (string or DesignSchema).
            KeyError: If `alias_dep` is a string but the corresponding library is not loaded.
            ValueError: If `src_fileset` is not found in `src_dep`, or if `alias_fileset` is
                        not found in `alias_dep` (when `alias_fileset` is not None).
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
        Checks if a library with the given name exists and is loaded in the project.

        Args:
            library (Union[str, NamedSchema]): The name of the library (string)
                                               or a `NamedSchema` object representing the library.

        Returns:
            bool: True if the library exists, False otherwise.
        """

        if isinstance(library, NamedSchema):
            library = library.name

        return library in self.getkeys("library")

    def _summary_headers(self) -> List[Tuple[str, str]]:
        """
        Generates a list of key-value pairs representing project-specific headers
        to be included in the summary report.

        This method provides information about the selected design, filesets,
        any active aliases, and the job directory. Projects can extend this
        method to add custom information to their summaries.

        Returns:
            List[Tuple[str, str]]: A list of tuples, where each tuple contains
                                   a header name (str) and its corresponding value (str).
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
        Generates a list of key-value pairs representing project-specific
        information to be included in snapshots.

        This method provides basic information about the design used in the
        snapshot. Projects can extend this method to add custom information.

        Returns:
            List[Tuple[str, str]]: A list of tuples, where each tuple contains
                                   an information label (str) and its corresponding value (str).
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
        Returns the absolute path of a compilation result file.

        This utility function constructs and returns the absolute path to a
        result file based on the provided arguments. The typical result
        directory structure is:
        `<build_dir>/<design_name>/<job_name>/<step>/<index>/<directory>/<design>.<filetype>`

        Args:
            filetype (str, optional): The file extension (e.g., 'v', 'def', 'gds').
                                      Required if `filename` is not provided.
            step (str, optional): The name of the task step (e.g., 'syn', 'place').
                                  Required.
            index (str, optional): The task index within the step. Defaults to "0".
            directory (str, optional): The node directory within the step to search
                                       (e.g., 'outputs', 'reports'). Defaults to "outputs".
            filename (str, optional): The exact filename to search for. If provided,
                                      `filetype` is ignored for constructing the path.
                                      Defaults to None.

        Returns:
            str: The absolute path to the found file, or None if the file is not found.

        Raises:
            ValueError: If `step` is not provided, or if `[option,fileset]` is not set
                        when `filename` is not provided.

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
        Creates a snapshot image summarizing the job's progress and key information.

        This function generates a PNG image that provides a visual overview
        of the compilation job. The image can be saved to a specified path
        and optionally displayed after generation.

        Args:
            path (str, optional): The file path where the snapshot image should be saved.
                                  If not provided, it defaults to
                                  `<job_directory>/<design_name>.png`.
            display (bool, optional): If True, the generated image will be opened for viewing
                                      if the system supports it and `option,nodisplay` is False.
                                      Defaults to True.

        Examples:
            >>> chip.snapshot()
            Creates a snapshot image in the default location.
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
        Opens a graphical viewer for a specified file or the last generated layout.

        The `show` function identifies an appropriate viewer tool based on the
        file's extension and the registered showtools. Display settings and
        technology-specific viewing configurations are read from the project's
        in-memory schema. All temporary rendering and display files are stored
        in a dedicated `_show_<jobname>` directory within the build directory.

        If no `filename` is provided, the method attempts to automatically find
        the last generated layout file in the build directory based on supported
        extensions from registered showtools.

        Args:
            filename (path, optional): The path to the file to display. If None,
                                       the system attempts to find the most recent
                                       layout file. Defaults to None.
            screenshot (bool, optional): If True, the operation is treated as a
                                         screenshot request, using `ScreenshotTaskSchema`
                                         instead of `ShowTaskSchema`. Defaults to False.
            extension (str, optional): The specific file extension to search for when
                                       automatically finding a file (e.g., 'gds', 'lef').
                                       Used only if `filename` is None. Defaults to None.

        Returns:
            str: The path to the generated screenshot file if `screenshot` is True,
                 otherwise None.

        Examples:
            >>> show('build/oh_add/job0/write.gds/0/outputs/oh_add.gds')
            Displays a GDS file using a viewer assigned by the showtool.
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
