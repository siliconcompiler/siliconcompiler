import logging
import os
import sys
import uuid

import os.path

from typing import Union, List, Tuple, TextIO, Optional, Dict, Set

from siliconcompiler.schema import BaseSchema, NamedSchema, EditableSchema, Parameter, Scope, \
    __version__ as schema_version, \
    LazyLoad

from siliconcompiler import Design
from siliconcompiler import Flowgraph
from siliconcompiler import Checklist

from siliconcompiler.schema_support.record import RecordSchema
from siliconcompiler.schema_support.metric import MetricSchema
from siliconcompiler import Task
from siliconcompiler import ShowTask, ScreenshotTask
from siliconcompiler.schema_support.option import OptionSchema
from siliconcompiler.library import LibrarySchema

from siliconcompiler.schema_support.cmdlineschema import CommandLineSchema
from siliconcompiler.schema_support.dependencyschema import DependencySchema
from siliconcompiler.schema_support.pathschema import PathSchemaBase

from siliconcompiler.report.dashboard.cli import CliDashboard
from siliconcompiler.scheduler import Scheduler, SCRuntimeError
from siliconcompiler.utils.logging import SCColorLoggerFormatter, SCLoggerFormatter
from siliconcompiler.utils import get_file_ext
from siliconcompiler.utils.multiprocessing import MPManager
from siliconcompiler.utils.paths import jobdir, workdir
from siliconcompiler.flows.showflow import ShowFlow


class Project(PathSchemaBase, CommandLineSchema, BaseSchema):
    """
    The Project class is the core object in SiliconCompiler, representing a
    complete hardware design project. It manages design parameters, libraries,
    flowgraphs, metrics, and provides methods for compilation, data collection,
    and reporting.
    """

    def __init__(self, design: Optional[Union[Design, str]] = None):
        """
        Initializes a new Project instance.

        This sets up the fundamental schema for the project, including global options,
        default libraries, flowgraphs, and tool configurations. It also initializes
        the project-specific logger and working directory.

        Args:
            design (Union[Design, str], optional): The top-level design for the
                project. Can be a `Design` object or the name of the design as a
                string. Defaults to None.
        """
        super().__init__()

        # Initialize schema
        schema = EditableSchema(self)

        # Version
        schema.insert(
            BaseSchema._version_key,
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                defvalue=schema_version,
                require=True,
                shorthelp="Schema version number",
                lock=True,
                example=["api: project.get('schemaversion')"],
                schelp="""SiliconCompiler schema version number."""))

        # Runtime arg
        schema.insert(
            'arg', 'step',
            Parameter(
                'str',
                scope=Scope.SCRATCH,
                shorthelp="ARG: step argument",
                switch="-arg_step <str>",
                example=["cli: -arg_step 'route'",
                         "api: project.set('arg', 'step', 'route')"],
                schelp="""
                Dynamic parameter passed in by the SC runtime as an argument to
                a runtime task. The parameter enables configuration code
                (usually TCL) to use control flow that depend on the current
                'step'. The parameter is used by the :meth:`.Project.run()` function and
                is not intended for external use."""))

        schema.insert(
            'arg', 'index',
            Parameter(
                'str',
                scope=Scope.SCRATCH,
                shorthelp="ARG: index argument",
                switch="-arg_index <str>",
                example=["cli: -arg_index 0",
                         "api: project.set('arg', 'index', '0')"],
                schelp="""
                Dynamic parameter passed in by the SC runtime as an argument to
                a runtime task. The parameter enables configuration code
                (usually TCL) to use control flow that depend on the current
                'index'. The parameter is used by the :meth:`.Project.run()` function and
                is not intended for external use."""))

        schema.insert("checklist", "default", Checklist())
        schema.insert("library", _ProjectLibrary())
        schema.insert("flowgraph", "default", Flowgraph())
        schema.insert("metric", MetricSchema())
        schema.insert("record", RecordSchema())
        schema.insert("tool", "default", "task", "default", Task())

        schema.insert("option", OptionSchema())

        # Add history
        schema.insert("history", BaseSchema())

        # Init logger
        self.__init_logger()

        # Init fields
        self.__cwd = os.getcwd()

        # Init options callbacks
        self.__init_option_callbacks()

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
        self.__logger = MPManager.logger().getChild(f"project_{uuid.uuid4().hex}")
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

    def __init_option_callbacks(self):
        """Initializes and registers callback functions for schema options.

        This internal method links specific configuration parameters to actions
        that should be performed when those parameters change.

        Currently, it registers a callback to initialize or re-initialize the
        dashboard object whenever the 'option, nodashboard' key is modified.
        """

        self.option._add_callback("nodashboard", self.__init_dashboard)

    def set(self, *args, field='value', clobber=True, step=None, index=None):
        if args[0:1] == ("option",):
            return self.option.set(*args[1:], field=field, clobber=clobber, step=step, index=index)

        return super().set(*args, field=field, clobber=clobber, step=step, index=index)

    @property
    def logger(self) -> logging.Logger:
        """
        Returns the logger for this project.

        Returns:
            logging.Logger: The project-specific logger instance.
        """
        return self.__logger

    @property
    def name(self) -> str:
        """
        Returns the name of the design.

        Returns:
            str: The name of the top-level design.
        """
        return self.get("option", "design")

    @property
    def design(self) -> Design:
        """
        Returns the design object associated with the project.

        Returns:
            Design: The `Design` schema object for the current project.

        Raises:
            ValueError: If the design name is not set.
            KeyError: If the design has not been loaded into the project's libraries.
        """
        design_name = self.name
        if not design_name:
            raise ValueError("design name is not set")
        if not self.valid("library", design_name):
            raise KeyError(f"{design_name} design has not been loaded")

        return self.get("library", design_name, field="schema")

    @property
    def option(self) -> OptionSchema:
        """
        Provides access to the top-level options schema.

        This property is the entry point for configuring global and job-specific
        parameters that control the compiler's behavior, such as flow control,
        logging, and build settings.

        Returns:
            OptionSchema: The schema object for top-level options.
        """
        return self.get("option", field="schema")

    @classmethod
    def convert(cls, obj: "Project") -> "Project":
        """
        Converts a project from one type to another (e.g., Project to Sim).

        Args:
            obj (Project): Source object to convert from.

        Returns:
            Project: A new object of the target class type, populated with
                     compatible data from the source object.

        Raises:
            TypeError: If the source object is not an instance of `Project`.
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
        Returns the object type metadata for `getdict` serialization.

        Returns:
            str: The name of the `Project` class.
        """
        return Project.__name__

    def _from_dict(self, manifest: Dict,
                   keypath: Union[List[str], Tuple[str, ...]],
                   version: Optional[Tuple[int, ...]] = None,
                   lazyload: LazyLoad = LazyLoad.ON) \
            -> Tuple[Set[Tuple[str, ...]], Set[Tuple[str, ...]]]:
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
        ret = super()._from_dict(manifest, keypath, version=version, lazyload=lazyload)

        if not lazyload.is_enforced:
            # Preserve logger in history
            for history in self.getkeys("history"):
                hist: "Project" = self.get("history", history, field="schema")
                hist.__logger = self.__logger

        return ret

    def add_dep(self, obj):
        """
        Adds a dependency object (e.g., a Design, Flowgraph, LibrarySchema,
        or Checklist) to the project.

        This method intelligently adds various types of schema objects to the
        project's internal structure. It also handles recursive addition of
        dependencies if the added object itself is a `DependencySchema`.

        Args:
            obj (Union[Design, Flowgraph, LibrarySchema, Checklist, List, Set, Tuple]):
                The dependency object(s) to add. Can be a single schema object
                or a collection (list, set, tuple) of schema objects.

        Raises:
            NotImplementedError: If the type of the object is not supported.
        """
        if isinstance(obj, (list, set, tuple)):
            for iobj in obj:
                self.add_dep(iobj)
            return

        if isinstance(obj, Design):
            if not self._has_library(obj.name):
                EditableSchema(self).insert("library", obj.name, obj)
        elif isinstance(obj, Flowgraph):
            self.__import_flow(obj)
        elif isinstance(obj, LibrarySchema):
            if not self._has_library(obj.name):
                EditableSchema(self).insert("library", obj.name, obj)
        elif isinstance(obj, Checklist):
            if obj.name not in self.getkeys("checklist"):
                EditableSchema(self).insert("checklist", obj.name, obj)
        else:
            raise NotImplementedError

        # Copy dependencies into project
        self._import_dep(obj)

    def _import_dep(self, obj: DependencySchema):
        """
        Recursively imports dependencies from a given schema object into the project.

        If the object is a `DependencySchema`, this method iterates through its
        dependencies, adds them to the project, and then rebuilds the dependency
        graph to ensure all pointers are correct.

        Args:
            obj (DependencySchema): The schema object whose dependencies are to be imported.
        """
        if isinstance(obj, DependencySchema):
            for dep in obj.get_dep():
                self.add_dep(dep)

            # Rebuild dependencies to ensure instances are correct
            self.get("library", field="schema")._populate_deps(obj)

    def __import_flow(self, flow: Flowgraph):
        """
        Imports a Flowgraph into the project.

        If the flowgraph with the given name is not already present, it is
        added to the project's flowgraph schema. This method also instantiates
        and registers all tasks defined within the imported flowgraph, ensuring
        that the necessary tool and task schemas are available.

        Args:
            flow (Flowgraph): The flowgraph schema object to import.
        """
        if flow.name in self.getkeys("flowgraph"):
            return

        edit_schema = EditableSchema(self)

        # Instantiate tasks
        for task_cls in flow.get_all_tasks():
            task = task_cls()
            if not self.valid("tool", task.tool(), "task", task.task()):
                edit_schema.insert("tool", task.tool(), "task", task.task(), task)
            else:
                existing_task: Task = self.get("tool", task.tool(), "task", task.task(),
                                               field="schema")
                if type(existing_task) is not type(task):
                    raise TypeError(f"Task {task.tool()}/{task.task()} already exists with "
                                    f"different type {type(existing_task).__name__}, "
                                    f"imported type is {type(task).__name__}")

        edit_schema.insert("flowgraph", flow.name, flow)

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
            if not self._has_library(design):
                self.logger.error(f"{design} has not been loaded")
                error = True

        # Assert fileset is set
        filesets = self.get("option", "fileset")
        if not filesets:
            self.logger.error("[option,fileset] has not been set")
            error = True
        elif design:  # Only check fileset in design if design is valid
            # Assert fileset is in design
            design_obj = self.design
            for fileset in filesets:
                if not design_obj.has_fileset(fileset):
                    self.logger.error(f"{fileset} is not a valid fileset in {design}")
                    error = True

            # Assert design has topmodule
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
        aliases = self.get("option", "alias") or []
        for src_lib, src_fileset, dst_lib, dst_fileset in aliases:
            if not src_lib:
                self.logger.error("source library in [option,alias] must be set")
                error = True
                continue

            if not self._has_library(src_lib):
                continue

            if not self.get("library", src_lib, field="schema").has_fileset(src_fileset):
                self.logger.error(f"{src_fileset} is not a valid fileset in {src_lib}")
                error = True
                continue

            if not dst_lib:
                continue

            if not self._has_library(dst_lib):
                self.logger.error(f"{dst_lib} has not been loaded")
                error = True
                continue

            if dst_fileset and \
                    not self.get("library", dst_lib, field="schema").has_fileset(dst_fileset):
                self.logger.error(f"{dst_fileset} is not a valid fileset in {dst_lib}")
                error = True
                continue

        # Check flowgraph tasks (runtime checks happen later)

        return not error

    def _init_run(self):
        """
        Method called before :meth:`.Project.check_manifest()` to provide a mechanism to
        setup the project correctly for a run.
        """
        # Automatically select fileset if only one is available in the design
        if not self.get("option", "fileset") and self.get("option", "design") and \
                self._has_library(self.get("option", "design")):
            filesets = self.design.getkeys("fileset")
            if len(filesets) == 1:
                fileset = filesets[0]
                self.logger.warning(f"Setting design fileset to: {fileset}")
                self.set("option", "fileset", fileset)

        # Disable dashboard if breakpoints are set
        if self.__dashboard and self.get("option", "flow"):
            breakpoints = set()
            flow = self.get("flowgraph", self.get("option", "flow"), field="schema")
            for step, index in flow.get_nodes():
                if self.get("option", "breakpoint", step=step, index=index):
                    breakpoints.add((step, index))
            if breakpoints and self.__dashboard.is_running():
                breakpoints = sorted(breakpoints)
                self.logger.info("Disabling dashboard due to breakpoints at: "
                                 f"{', '.join([f'{step}/{index}' for step, index in breakpoints])}")
                self.__dashboard.stop()

    def run(self) -> "Project":
        '''
        Executes the compilation flow defined in the project's flowgraph.

        The run method orchestrates the entire compilation process. It starts by
        initializing the dashboard and then hands off execution to a `Scheduler`
        (or `ClientScheduler` for remote runs). The scheduler manages the
        step-by-step execution of tasks defined in the flowgraph, respecting
        dependencies and handling errors.

        After the scheduler completes, the dashboard is updated with the final
        run status, and non-global job parameters are reset. The method returns
        a `Project` object representing the completed job's history.

        Returns:
            Project: A mutable reference to the completed job's record in the
                     project history.

        Examples:
            >>> project.run()
            # Executes the flow, and returns a project object for the completed job.
        '''
        from siliconcompiler.remote import ClientScheduler

        # Start dashboard
        if self.__dashboard:
            if not self.__dashboard.is_running():
                self.__dashboard.open_dashboard()
            # Attach logger
            self.__dashboard.set_logger(self.logger)

        scheduler = None
        try:
            if self.get('option', 'remote'):
                scheduler = ClientScheduler(self)
            else:
                scheduler = Scheduler(self)
            scheduler.run()
        except SCRuntimeError as e:
            self.logger.error(f"Run failed: {e.msg}")
            if scheduler and scheduler.log:
                self.logger.error(f"Job log: {os.path.abspath(scheduler.log)}")
            raise RuntimeError(f"Run failed: {e.msg}")
        finally:
            if self.__dashboard:
                # Update dashboard
                self.__dashboard.update_manifest()
                self.__dashboard.end_of_run()

        self.__reset_job_params()

        return self.history(self.get("option", "jobname"))

    def __reset_job_params(self):
        """
        Resets all non-global schema parameters after a run.

        This method iterates through all parameters in the schema and calls
        `reset()` on any parameter that does not have a 'global' scope,
        clearing task-specific values for the next run.
        """
        for key in self.allkeys():
            if key[0] == "history":
                continue
            param = self.get(*key, field=None)
            if param.get(field="scope") != Scope.GLOBAL:
                param.reset()

    def history(self, job: str) -> "Project":
        '''
        Returns a *mutable* reference to a historical job record as a Project object.

        Args:
            job (str): Name of the historical job to retrieve.

        Returns:
            Project: The `Project` object representing the specified historical job.

        Raises:
            KeyError: If the specified job does not exist in the history.
        '''
        if job not in self.getkeys("history"):
            raise KeyError(f"{job} is not a valid job")

        return self.get("history", job, field="schema")

    def _record_history(self):
        '''
        Copies the current project state into the history record.
        '''
        job = self.get("option", "jobname")
        proj = self.copy()

        # Preserve logger instance
        proj.__logger = self.__logger

        # Remove history from the copy to avoid recursion
        EditableSchema(proj).insert("history", BaseSchema(), clobber=True)

        if job in self.getkeys("history"):
            self.logger.warning(f"Overwriting job {job}")

        EditableSchema(self).insert("history", job, proj, clobber=True)

    def __getstate__(self):
        """
        Prepares the project's state for serialization (pickling).

        Removes non-serializable objects like the logger and dashboard, and
        stores the multiprocessing manager's address for reconstruction.

        Returns:
            dict: The serializable state of the object.
        """
        # Ensure a copy of the state is used
        state = self.__dict__.copy()

        # Remove logger objects since they are not serializable
        del state["_Project__logger"]
        del state["_logger_console"]

        # Remove dashboard
        del state["_Project__dashboard"]

        # Pass along manager address
        state["__manager__"] = MPManager._get_manager_address()

        # Pass along logger level
        state["__loglevel__"] = self.logger.level

        return state

    def __setstate__(self, state):
        """
        Restores the project's state from a deserialized (unpickled) state.

        Re-initializes non-serializable objects like the logger and dashboard
        after restoring the core object dictionary.

        Args:
            state (dict): The deserialized state of the object.
        """
        # Retrieve log level
        loglevel = state["__loglevel__"]
        del state["__loglevel__"]

        # Retrieve manager address
        MPManager._set_manager_address(state["__manager__"])
        del state["__manager__"]

        self.__dict__ = state

        # Reinitialize logger on restore
        self.__init_logger()
        self.logger.setLevel(loglevel)

        # Restore callbacks
        self.__init_option_callbacks()

        # Restore dashboard
        self.__init_dashboard()

    def get_filesets(self) -> List[Tuple[NamedSchema, str]]:
        """
        Returns the filesets selected for this project, resolving any aliases.

        This method retrieves the filesets defined in :keypath:`option,fileset`
        and applies any aliases specified in :keypath:`option,alias` to return
        the effective list of filesets and their parent libraries.

        Returns:
            List[Tuple[NamedSchema, str]]: A list of tuples, where each tuple
            contains the parent library (`NamedSchema`) and the fileset name (str).

        Raises:
            KeyError: If an alias points to a library that is not loaded.
        """
        # Build alias mapping
        alias = {}
        for src_lib, src_fileset, dst_lib, dst_fileset in self.get("option", "alias"):
            if dst_lib:
                if not self._has_library(dst_lib):
                    raise KeyError(f"{dst_lib} is not a loaded library")
                dst_obj = self.get("library", dst_lib, field="schema")
            else:
                dst_obj = None
            if not dst_fileset:
                dst_fileset = None
            alias[(src_lib, src_fileset)] = (dst_obj, dst_fileset)

        return self.design.get_fileset(self.get("option", "fileset"), alias=alias)

    def set_design(self, design: Union[Design, str]):
        """
        Sets the active design for this project.

        This method allows you to specify the primary design that the project
        will operate on. If a `Design` object is provided, it is first
        added as a dependency.

        Args:
            design (Union[Design, str]): The design object or its name (string)
                                               to be set as the current design.

        Raises:
            TypeError: If the provided `design` is not a string or a `Design` object.
        """
        if isinstance(design, Design):
            self.add_dep(design)
            design = design.name
        elif not isinstance(design, str):
            raise TypeError("design must be a string or a Design object")

        return self.set("option", "design", design)

    def set_flow(self, flow: Union[Flowgraph, str]):
        """
        Sets the active flowgraph for this project.

        This method allows you to specify the sequence of steps and tasks
        (the flow) that the project will execute. If a `Flowgraph` object
        is provided, it is first added as a dependency.

        Args:
            flow (Union[Flowgraph, str]): The flowgraph object or its name (string)
                                                to be set as the current flow.

        Raises:
            TypeError: If the provided `flow` is not a string or a `Flowgraph` object.
        """
        if isinstance(flow, Flowgraph):
            self.add_dep(flow)
            flow = flow.name
        elif not isinstance(flow, str):
            raise TypeError("flow must be a string or a Flowgraph object")

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
        if isinstance(fileset, str):
            fs_list = [fileset]
        elif isinstance(fileset, (list, tuple, set)):
            if not all(isinstance(v, str) for v in fileset):
                raise TypeError("fileset must be a string or a list/tuple/set of strings")
            fs_list = list(fileset)
        else:
            raise TypeError("fileset must be a string or a list/tuple/set of strings")

        for fs in fs_list:
            if not self.design.has_fileset(fs):
                raise ValueError(f"{fs} is not a valid fileset in {self.design.name}")

        if clobber:
            return self.set("option", "fileset", fs_list)
        else:
            return self.add("option", "fileset", fs_list)

    def add_alias(self,
                  src_dep: Union[Design, str],
                  src_fileset: str,
                  alias_dep: Union[Design, str],
                  alias_fileset: str,
                  clobber: bool = False):
        """
        Adds an aliased fileset mapping to the project.

        This method allows you to redirect a fileset reference from a source
        library/fileset to a different destination library/fileset. This is
        useful for substituting design components or test environments without
        modifying the original design.

        Args:
            src_dep (Union[Design, str]): The source design library (object or name)
                                                from which the fileset is being aliased.
            src_fileset (str): The name of the source fileset to alias.
            alias_dep (Union[Design, str]): The destination design library (object or name)
                                                  to which the fileset is being redirected.
                                                  Can be None or an empty string to indicate
                                                  deletion.
            alias_fileset (str): The name of the destination fileset. Can be None or an empty string
                                 to indicate deletion of the fileset reference.
            clobber (bool): If True, any existing alias for `(src_dep, src_fileset)` will be
                            overwritten. If False, the alias will be added. Defaults to False.

        Raises:
            TypeError: If `src_dep` or `alias_dep` are not valid types (string or Design).
            KeyError: If `alias_dep` is a string but the corresponding library is not loaded.
            ValueError: If `src_fileset` is not found in `src_dep`, or if `alias_fileset` is
                        not found in `alias_dep` (when `alias_fileset` is not None).
        """

        if isinstance(src_dep, str):
            if self._has_library(src_dep):
                src_dep = self.get("library", src_dep, field="schema")
            else:
                src_dep_name = src_dep
                src_dep = None

        if src_dep is not None:
            if isinstance(src_dep, Design):
                src_dep_name = src_dep.name
                if not self._has_library(src_dep_name):
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
                if not self._has_library(alias_dep):
                    raise KeyError(f"{alias_dep} has not been loaded")

                alias_dep = self.get("library", alias_dep, field="schema")

        if alias_dep is not None:
            if isinstance(alias_dep, Design):
                alias_dep_name = alias_dep.name
                if not self._has_library(alias_dep_name):
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

    def _has_library(self, library: Union[str, NamedSchema]) -> bool:
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
        Generates key-value pairs for project-specific headers in the summary report.

        This method provides information about the selected design, filesets,
        any active aliases, and the job directory. Projects can extend this
        method to add custom information to their summaries.

        Returns:
            List[Tuple[str, str]]: A list of tuples, where each tuple contains
                                   a header name (str) and its corresponding value (str).
        """

        alias = []
        for src, src_fs, dst, dst_fs in self.get("option", "alias"):
            if not self._has_library(src):
                continue
            if dst and not self._has_library(dst):
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
        headers.append(("jobdir", jobdir(self)))

        return headers

    def _snapshot_info(self) -> List[Tuple[str, str]]:
        """
        Generates key-value pairs for project-specific information in snapshots.

        This method provides basic information about the design used in the
        snapshot. Projects can extend this method to add custom information.

        Returns:
            List[Tuple[str, str]]: A list of tuples, where each tuple contains
                                   an information label (str) and its corresponding value (str).
        """
        return [("Design", self.get("option", "design"))]

    def summary(self, jobname: str = None, fd: TextIO = None) -> None:
        '''
        Prints a summary of the compilation manifest and results.

        Metrics from the specified job are printed out on a per-step basis.

        Args:
            jobname (str, optional): The name of the job to summarize. If not
                provided, the value in :keypath:`option,jobname` will be used.
            fd (TextIO, optional): If provided, prints the summary to this file
                descriptor instead of stdout.

        Raises:
            ValueError: If there is no history to summarize.

        Examples:
            >>> project.summary()
            # Prints a summary of the last run to stdout.
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

        if not fd:
            if self.__dashboard and self.__dashboard.is_running():
                self.__dashboard.stop()

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
            step (str): The name of the task step (e.g., 'syn', 'place'). Required.
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
            >>> # Get path to gate-level Verilog from synthesis step
            >>> vg_filepath = project.find_result('vg', step='syn')
        """

        if filename and step is None:
            step = filetype

        if step is None:
            raise ValueError("step is required")

        workingdir = workdir(self, step, index)

        if not filename:
            fileset = self.get("option", "fileset")
            if not fileset:
                raise ValueError("[option,fileset] is not set")
            design_name = self.design.get_topmodule(fileset[0])

            checkfiles = [
                os.path.join(workingdir, directory, f'{design_name}.{filetype}'),
                os.path.join(workingdir, directory, f'{design_name}.{filetype}.gz')
            ]
        else:
            checkfiles = [os.path.join(workingdir, directory, filename)]

        for f in checkfiles:
            self.logger.debug(f"Finding node file: {f}")
            if os.path.exists(f):
                return os.path.abspath(f)

        return None

    def snapshot(self, path: str = None, jobname: str = None, display: bool = True) -> None:
        '''
        Creates a snapshot image summarizing a job's progress and key information.

        This function generates a PNG image that provides a visual overview
        of the compilation job.

        Args:
            path (str, optional): The file path where the snapshot image should be saved.
                                  If not provided, it defaults to
                                  `<job_directory>/<design_name>.png`.
            jobname (str, optional): The job to snapshot. If not provided, the value
                                   in :keypath:`option,jobname` will be used.
            display (bool, optional): If True, the generated image will be opened for viewing
                                      if the system supports it and `option,nodisplay` is False.
                                      Defaults to True.

        Raises:
            ValueError: If there is no history to snapshot.

        Examples:
            >>> project.snapshot()
            # Creates a snapshot image in the default location for the last run.
        '''
        from siliconcompiler.report import generate_summary_image, _open_summary_image

        histories = self.getkeys("history")
        if not histories:
            raise ValueError("no history to snapshot")

        if jobname is None:
            jobname = self.get("option", "jobname")
        if jobname not in histories:
            org_job = jobname
            jobname = histories[0]
            self.logger.warning(f"{org_job} not found in history, picking {jobname}")

        history = self.history(jobname)

        if not path:
            path = os.path.join(jobdir(history), f'{history.design.name}.png')

        if os.path.exists(path):
            os.remove(path)

        generate_summary_image(history, path, history._snapshot_info())

        if os.path.isfile(path) and not self.get('option', 'nodisplay') and display:
            _open_summary_image(path)

    def show(self, filename: str = None, screenshot: bool = False, extension: str = None) -> str:
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
            filename (str, optional): The path to the file to display. If None,
                                      the system attempts to find the most recent
                                      layout file. Defaults to None.
            screenshot (bool): If True, the operation is treated as a screenshot request,
                               using `ScreenshotTask` instead of `ShowTask`.
                               Defaults to False.
            extension (str, optional): The specific file extension to search for when
                                       automatically finding a file (e.g., 'gds', 'lef').
                                       Used only if `filename` is None. Defaults to None.

        Returns:
            str: The path to the generated screenshot file if `screenshot` is True,
                 otherwise None.

        Examples:
            >>> # Display a specific GDS file
            >>> project.show('build/my_design/job0/write_gds/0/outputs/my_design.gds')

            >>> # Automatically find and show the last generated layout
            >>> project.show()
        '''
        tool_cls = ScreenshotTask if screenshot else ShowTask

        sc_jobname = self.option.get_jobname()
        sc_step, sc_index = None, None

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
            return None

        filepath = os.path.abspath(filename)

        if not has_filename:
            self.logger.info(f'Showing file {filename}')

        # Check that file exists
        if not os.path.exists(filepath):
            self.logger.error(f"Invalid filepath {filepath}.")
            return None

        filetype = get_file_ext(filepath)

        task = tool_cls.get_task(filetype)
        if task is None:
            self.logger.error(f"Filetype '{filetype}' not available in the registered showtools.")
            return None

        # Create copy of project to avoid changing user project
        proj: Project = self.copy()
        proj.set_flow(ShowFlow(task))

        # Setup options:
        for option, value in [
                ("track", False),
                ("remote", False),
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

        jobname = f"_{task.task()}_{sc_jobname}_{sc_step}_{sc_index}_{task.tool()}"
        proj.set("option", "jobname", jobname)

        # Setup in task variables
        task: ShowTask = task.find_task(proj)
        task.set_showfilepath(filename)
        task.set_showfiletype(filetype)
        task.set_shownode(jobname=sc_jobname, step=sc_step, index=sc_index)

        # run show flow
        proj.run()
        if screenshot:
            return proj.find_result('png', step=task.task())


class Sim(Project):
    """
    A specialized Project class tailored for simulation tasks.

    This class can be extended with simulation-specific schema parameters,
    methods, and flows.
    """

    @classmethod
    def _getdict_type(cls) -> str:
        return Sim.__name__


class Lint(Project):
    """
    A specialized Project class tailored for linting tasks.

    This class can be extended with linting-specific schema parameters,
    methods, and flows.
    """

    @classmethod
    def _getdict_type(cls) -> str:
        return Lint.__name__


class _ProjectLibrary(BaseSchema):
    def _from_dict(self, manifest: Dict,
                   keypath: Union[List[str], Tuple[str, ...]],
                   version: Optional[Tuple[int, ...]] = None,
                   lazyload: LazyLoad = LazyLoad.ON) \
            -> Tuple[Set[Tuple[str, ...]], Set[Tuple[str, ...]]]:
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
        ret = super()._from_dict(manifest, keypath, version=version, lazyload=lazyload)

        if not lazyload.is_enforced:
            # Restore dependencies
            self._populate_deps(complete=True)

        return ret

    def _populate_deps(self, obj: Optional[DependencySchema] = None, complete: bool = False):
        """
        Ensures that all loaded dependencies (like libraries) within the project
        contain correct internal pointers back to the project's libraries.
        This is crucial for maintaining a consistent and navigable schema graph.

        Args:
            obj (DependencySchema, optional): An optional dependency object to
                reset and populate. If None, all existing library dependencies
                in the project are processed. Defaults to None.
            complete (bool, optional): If True, performs a full reset of all
                DependencySchema objects before populating dependencies. This
                ensures a clean state during manifest deserialization. Defaults to False.
        """
        if obj:
            obj._reset_deps()
        dep_map = {name: self.get(name, field="schema") for name in self.getkeys()}

        if complete:
            for obj in dep_map.values():
                if isinstance(obj, DependencySchema):
                    obj._reset_deps()

        for obj in dep_map.values():
            if isinstance(obj, DependencySchema):
                obj._populate_deps(dep_map)
