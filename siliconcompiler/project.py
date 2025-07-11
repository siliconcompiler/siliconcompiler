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


class Project(BaseSchema):
    def __init__(self):
        super().__init__()

        self.__design_name = None

        # Initialize schema
        schema = EditableSchema(self)
        schema.insert("design", "default", DesignSchema())
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

        schema.insert("option", "alias", Parameter("(str,str,str,str)"))
        schema.insert("option", "fileset", Parameter("(str,str)"))
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
    def logger(self):
        return self.__logger

    @property
    def design(self):
        if self.__design_name:
            return self.__design_name

        if len(self.getkeys("design")) == 1:
            self.__design_name = self.getkeys("design")[0]
            return self.__design_name

        raise ValueError("Unable to determine design name")

    @design.setter
    def set_design(self, design):
        self.__design_name = design.name()

    def top(self):
        return self.get("design", self.design, field="schema").name()

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
        if not self.__design_name:
            self.__design_name = design.name()

        edit_schema.insert("design", design.name(), design, clobber=True)

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
                   self.design,
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
