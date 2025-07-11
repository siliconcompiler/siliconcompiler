import logging
import os
import sys

import os.path

from siliconcompiler.schema import BaseSchema, EditableSchema, Parameter

from siliconcompiler.design import DesignSchema
from siliconcompiler.flowgraph import FlowgraphSchema
from siliconcompiler.record import RecordSchema
from siliconcompiler.metric import MetricSchema
from siliconcompiler.checklist import ChecklistSchema
from siliconcompiler.tool import ToolSchema
from siliconcompiler.packageschema import PackageSchema
from siliconcompiler.pdk import PDKSchema
from siliconcompiler.schema.schema_cfg import schema_option_runtime

from siliconcompiler.scheduler.scheduler import Scheduler
from siliconcompiler.utils.logging import SCColorLoggerFormatter, \
    SCLoggerFormatter, SCInRunLoggerFormatter
from siliconcompiler.package import Resolver


class Project(BaseSchema):
    def __init__(self):
        super().__init__()

        # Initialize schema
        schema = EditableSchema(self)
        schema.insert("library", "default", DesignSchema())
        schema.insert("flowgraph", "default", FlowgraphSchema())
        schema.insert("record", RecordSchema())
        schema.insert("metric", MetricSchema())
        schema.insert("package", PackageSchema())
        schema.insert("checklist", "default", ChecklistSchema())
        schema.insert("tool", "default", ToolSchema())

        schema_option_runtime(schema)
        schema.insert("option", "env", "default", Parameter("str"))
        schema.insert("arg", "step", Parameter("str"))
        schema.insert("arg", "index", Parameter("str"))

        schema.insert("option", "alias", Parameter("[(str,str,str,str)]"))
        schema.insert("option", "fileset", Parameter("[str]"))
        schema.insert("option", "design", Parameter("str"))

        # Init logger
        self.__init_logger()

        # Init fields
        self.__cwd = os.getcwd()

        # Register root package
        self.get("package", field="schema").register(
            "siliconcompiler",
            "python://siliconcompiler")

    def __init_logger(self):
        sc_logger = logging.getLogger("siliconcompiler")
        sc_logger.propagate = False
        self.__logger = sc_logger.getChild(f"project_{id(self)}")
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
        return self.__logger

    @property
    def design(self) -> DesignSchema:
        return self.get("library", self.get("option", "design"), field="schema")

    @property
    def cwd(self):
        return self.__cwd

    def add_dep(self, obj):
        if isinstance(obj, DesignSchema):
            self.__import_design(obj)
        elif isinstance(obj, FlowgraphSchema):
            self.__import_flow(obj)

    def __import_design(self, design: DesignSchema):
        edit_schema = EditableSchema(self)
        edit_schema.insert("library", design.name(), design, clobber=True)

        for dep in design.get_dep(None):
            self.add_dep(dep)

        # TODO fix resolvers to lookup in relevant sections of schema
        for dep in [design, *design.get_dep(None)]:
            for package in dep.getkeys("package"):
                self.get("package", field="schema").register(
                    package,
                    dep.get("package", package, "root"),
                    dep.get("package", package, "tag"))

    def __import_flow(self, flow: FlowgraphSchema):
        edit_schema = EditableSchema(self)
        edit_schema.insert("flowgraph", flow.name(), flow, clobber=True)
        for task_cls in flow.get_all_tasks():
            task = task_cls()
            edit_schema.insert("tool", task.tool(), ToolSchema(), clobber=True)
            edit_schema.insert("tool", task.tool(), "task", task.task(), task, clobber=True)

    def check_manifest(self):
        # Assert design is set
        # Assert fileset is set
        # Assert flow is set

        # Assert design is a library
        # Assert fileset is in design
        # Assert design has topmodule

        # Check that alias libraries exist

        # Check flowgraph
        # Check tasks have classes, cannot check post setup that is a runtime check

        return True

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
            pass
            # Update dashboard if running
            # if self._dash:
            #     self._dash.update_manifest()
            #     self._dash.end_of_run()

        return True

    def __getbuilddir(self):
        dirlist = [self.cwd,
                   self.get('option', 'builddir')]
        return os.path.join(*dirlist)

    def getworkdir(self, step=None, index=None):
        dirlist = [self.__getbuilddir(),
                   self.design.name(),
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
        return os.path.join(self.getworkdir(), "sc_collected_files")

    def collect(self, **kwargs):
        pass

    def get_fileset_mapping(self):
        # Build alias mapping
        alias = {}
        for src_lib, src_fileset, dst_lib, dst_fileset in self.get("option", "alias"):
            if dst_lib:
                dst_obj = self.get("library", dst_lib, field="schema")
            else:
                dst_lib = None
            if not dst_fileset:
                dst_fileset = None
            alias[(src_lib, src_fileset)] = (dst_obj, dst_fileset)

        return self.design.get_fileset_mapping(self.get("option", "fileset"), alias=alias)

    def __getstate__(self):
        # Ensure a copy of the state is used
        state = self.__dict__.copy()

        # Remove logger since it is not serializable
        del state["_Project__logger"]
        del state["_logger_console"]

        return state

    def __setstate__(self, state):
        self.__dict__ = state

        # Reinitialize logger on restore
        self.__init_logger()

    def __get_resolver_map(self):
        """
        Generate the resolver map got package handling for find_files and check_filepaths
        """
        resolver_map = {}
        for package in self.getkeys("package", "source"):
            root = self.get("package", "source", package, "path")
            tag = self.get("package", "source", package, "ref")
            resolver = Resolver.find_resolver(root)
            resolver_map[package] = resolver(package, self, root, tag).get_path
        return resolver_map

    def find_files(self, *keypath,
                   missing_ok=False,
                   step=None, index=None):
        """
        Returns absolute paths to files or directories based on the keypath
        provided.

        The keypath provided must point to a schema parameter of type file, dir,
        or lists of either. Otherwise, it will trigger an error.

        Args:
            keypath (list of str): Variable length schema key list.
            missing_ok (bool): If True, silently return None when files aren't
                found. If False, print an error and set the error flag.
            step (str): Step name to access for parameters that may be specified
                on a per-node basis.
            index (str): Index name to access for parameters that may be specified
                on a per-node basis.

        Returns:
            If keys points to a scalar entry, returns an absolute path to that
            file/directory, or None if not found. It keys points to a list
            entry, returns a list of either the absolute paths or None for each
            entry, depending on whether it is found.

        Examples:
            >>> schema.find_files('input', 'verilog')
            Returns a list of absolute paths to source files, as specified in
            the schema.
        """
        return super().find_files(*keypath,
                                  missing_ok=missing_ok,
                                  step=step, index=index,
                                  packages=self.__get_resolver_map(),
                                  collection_dir=self.getcollectiondir(),
                                  cwd=self.cwd)

    def check_filepaths(self, ignore_keys=None):
        '''
        Verifies that paths to all files in manifest are valid.

        Args:
            ignore_keys (list of keypaths): list of keypaths to ignore while checking

        Returns:
            True if all file paths are valid, otherwise False.
        '''
        return super().check_filepaths(
            ignore_keys=ignore_keys,
            logger=self.logger,
            packages=self.__get_resolver_map(),
            collection_dir=self.getcollectiondir(),
            cwd=self.cwd)


class LintProject(Project):
    def __init__(self):
        super().__init__()


class ASICProject(Project):
    def __init__(self):
        super().__init__()

        schema = EditableSchema(self)
        schema.insert("pdk", "default", PDKSchema())

        schema.insert("asic", "logiclib", Parameter("[str]"))
        schema.insert("asic", "macrolib", Parameter("[str]"))  # TODO: is this needed?
        schema.insert("asic", "arch", Parameter("str"))

    def check_manifest(self):
        if not super().check_manifest():
            return False

        # Assert logic lib is set
        # Assert libs exists

        return True
