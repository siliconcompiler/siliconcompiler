import logging
import sys

from siliconcompiler.schema import BaseSchema, EditableSchema

from siliconcompiler.design import DesignSchema
from siliconcompiler.flowgraph import FlowgraphSchema
from siliconcompiler.record import RecordSchema
from siliconcompiler.metric import MetricSchema
from siliconcompiler.checklist import ChecklistSchema
from siliconcompiler.tool import ToolSchema
from siliconcompiler.schema.schema_cfg import schema_option_runtime

from siliconcompiler.scheduler.scheduler import Scheduler
from siliconcompiler.utils.logging import SCColorLoggerFormatter, \
    SCLoggerFormatter, SCInRunLoggerFormatter


class Runnable(BaseSchema):
    def __init__(self):
        super().__init__()

        # Initialize schema
        schema = EditableSchema(self)
        schema.insert("design", DesignSchema())
        schema.insert("flowgraph", "default", FlowgraphSchema())
        schema.insert("record", RecordSchema())
        schema.insert("metric", MetricSchema())
        schema.insert("checklist", "default", ChecklistSchema())
        schema.insert("tool", "default", ToolSchema())

        schema_option_runtime(schema)

        # Initialize logger
        console_handler = logging.StreamHandler(stream=sys.stdout)
        self.__logger_handlers = {
            "console": console_handler
        }
        self.__logger_color = SCColorLoggerFormatter.supports_color(console_handler)
        self.__init_logger()

    def __init_logger(self):
        sc_logger = logging.getLogger("siliconcompiler")
        sc_logger.propagate = False
        self.logger = sc_logger.getChild(f"runnable_{id(self)}")
        self.logger.propagate = False
        self.logger.setLevel(logging.INFO)

        for handler in self.__logger_handlers.values():
            self.logger.addHandler(handler)

        self.__init_logger_formats(None)

    def __init_logger_formats(self, jobname, step=None, index=None):
        formatter = SCLoggerFormatter()
        if jobname is not None:
            formatter = SCInRunLoggerFormatter(self, jobname, step, index)
        for name, handler in self.__logger_handlers.items():
            if name == "console" and self.__logger_color:
                handler.setFormatter(SCColorLoggerFormatter(formatter))
            else:
                handler.setFormatter(formatter)

    def add_dep(self, obj):
        pass

    def check(self):
        pass

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
            # Update dashboard if running
            if self._dash:
                self._dash.update_manifest()
                self._dash.end_of_run()

        return True
