import logging
import os
import sys
import uuid

import os.path

from typing import Union, List, Tuple

from siliconcompiler.schema import BaseSchema, NamedSchema, EditableSchema, Parameter

from siliconcompiler import DesignSchema
from siliconcompiler import FlowgraphSchema
from siliconcompiler import RecordSchema
from siliconcompiler import MetricSchema
from siliconcompiler import ChecklistSchema
from siliconcompiler import ToolSchema, TaskSchema

from siliconcompiler.pathschema import PathSchemaBase

from siliconcompiler.schema.schema_cfg import schema_option_runtime, schema_arg, schema_version

from siliconcompiler.scheduler.scheduler import Scheduler
from siliconcompiler.utils.logging import SCColorLoggerFormatter, SCLoggerFormatter


class Project(PathSchemaBase, BaseSchema):
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

        schema.insert("option", "alias", Parameter("[(str,str,str,str)]"))
        schema.insert("option", "fileset", Parameter("[str]"))
        schema.insert("option", "design", Parameter("str"))

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

    def add_dep(self, obj):
        if isinstance(obj, DesignSchema):
            self.__import_design(obj)
        elif isinstance(obj, FlowgraphSchema):
            self.__import_flow(obj)
        else:
            raise NotImplementedError

    def __import_design(self, design: DesignSchema):
        edit_schema = EditableSchema(self)
        edit_schema.insert("library", design.name, design, clobber=True)

        # Copy dependencies into project
        for dep in design.get_dep():
            self.add_dep(dep)

    def __import_flow(self, flow: FlowgraphSchema):
        edit_schema = EditableSchema(self)
        edit_schema.insert("flowgraph", flow.name, flow, clobber=True)

        # Instantiate tasks
        for task_cls in flow.get_all_tasks():
            task = task_cls()
            # TODO: this is not needed once tool moves
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

    def collect(self, **kwargs):
        pass

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

        return state

    def __setstate__(self, state):
        self.__dict__ = state

        # Reinitialize logger on restore
        self.__init_logger()

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
                 tool: str,
                 task: str,
                 step: str = None,
                 index: Union[str, int] = None) -> TaskSchema:
        if self.valid("tool", tool, "task", task):
            obj: TaskSchema = self.get("tool", tool, "task", task, field="schema")
            if step or index:
                with obj.runtime(None, step, index) as obj:
                    return obj
            return obj
        raise KeyError(f"{tool}/{task} has not been loaded")

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
            if fs not in self.design.getkeys("fileset"):
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
            if src_dep not in self.getkeys("library"):
                raise KeyError(f"{src_dep} has not been loaded")

            src_dep = self.get("library", src_dep, field="schema")
        if isinstance(src_dep, DesignSchema):
            src_dep_name = src_dep.name
            if src_dep_name not in self.getkeys("library"):
                raise KeyError(f"{src_dep_name} has not been loaded")
        else:
            raise TypeError("source dep is not a valid type")

        if src_fileset not in src_dep.getkeys("fileset"):
            raise ValueError(f"{src_dep_name} does not have {src_fileset} as a fileset")

        if alias_dep is None:
            alias_dep = ""

        if isinstance(alias_dep, str):
            if alias_dep == "":
                alias_dep = None
                alias_dep_name = ""
                alias_fileset = ""
            else:
                if alias_dep not in self.getkeys("library"):
                    raise KeyError(f"{alias_dep} has not been loaded")

                alias_dep = self.get("library", alias_dep, field="schema")

        if alias_dep is not None:
            if isinstance(alias_dep, DesignSchema):
                alias_dep_name = alias_dep.name
                if alias_dep_name not in self.getkeys("library"):
                    self.add_dep(alias_dep)
            else:
                raise TypeError("alias dep is not a valid type")

            if alias_fileset != "" and alias_fileset not in alias_dep.getkeys("fileset"):
                raise ValueError(f"{alias_dep_name} does not have {alias_fileset} as a fileset")

        alias = (src_dep_name, src_fileset, alias_dep_name, alias_fileset)
        if clobber:
            return self.set("option", "alias", alias)
        else:
            return self.add("option", "alias", alias)
