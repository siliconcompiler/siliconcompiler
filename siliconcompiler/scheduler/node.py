import shutil
import sys

import os.path

from logging.handlers import QueueHandler

from siliconcompiler import utils, sc_open
from siliconcompiler import Schema
from siliconcompiler import NodeStatus

from siliconcompiler.record import RecordTime, RecordTool
from siliconcompiler.schema import JournalingSchema
from siliconcompiler.scheduler import send_messages


class SchedulerNode:
    def __init__(self, chip, step, index, pipe=None, track=False):
        self.__step = step
        self.__index = index
        self.__chip = chip

        self.__design = self.__chip.design

        self.__job = self.__chip.get('option', 'jobname')
        self.__record_user_info = track
        self.__pipe = pipe
        self.__failed_log_lines = 20
        self.__error = False
        self.__generateTestCase = True

        self.__workdir = self.__chip.getworkdir(jobname=self.__job, step=self.__step, index=self.__index)
        self.__manifests = {
            "input": os.path.join(self.__workdir, "inputs", f"{self.__design}.pkg.json"),
            "output": os.path.join(self.__workdir, "outputs", f"{self.__design}.pkg.json")
        }
        self.__logs = {
            "sc": os.path.join(self.__workdir, f"sc_{self.__step}{self.__index}.log"),
            "exe": os.path.join(self.__workdir, f"{self.__step}.log")
        }
        self.__replay = os.path.join(self.__workdir, "replay.sh")

        self.setQueue(None)
        self.__setupSchemaAccess()

    @property
    def logger(self):
        return self.__chip.logger

    def setQueue(self, queue):
        self.__queue = queue

    def __setupSchemaAccess(self):
        flow = self.__chip.get('option', 'flow')
        tool = self.__chip.get('flowgraph', flow, self.__step, self.__index, 'tool')

        self.__task = self.__chip.schema.get("tool", tool, field="schema")
        self.__record = self.__chip.schema.get("record", field="schema")
        self.__metrics = self.__chip.schema.get("record", field="schema")

    def halt(self):
        self.__chip.schema.get("record", field='schema').set(
            "status", NodeStatus.ERROR,
            step=self.__step, index=self.__index)
        self.__chip.schema.write_manifest(self.__manifests["output"])

        self.logger.error(f"Halting {self.__step}{self.__index} due to errors.")
        send_messages.send(self.__chip, "fail", self.__step, self.__index)
        sys.exit(1)

    def setup(self):
        pass

    def requires_run(self):
        return True

    def run(self):
        '''
        Private per node run method called by run().

        The method takes in a step string and index string to indicate what
        to run.

        Note that since _runtask occurs in its own process with a separate
        address space, any changes made to the `self` object will not
        be reflected in the parent. We rely on reading/writing the chip manifest
        to the filesystem to communicate updates between processes.
        '''

        # Setup chip
        self.__chip._init_codecs()
        self.__chip._init_logger(self.__step, self.__index, in_run=True)

        if self.__queue:
            self.logger.removeHandler(self.logger._console)
            self.logger._console = QueueHandler(self.__queue)
            self.logger.addHandler(self.logger._console)
            self.__chip._init_logger_formats()

        self.__chip.set('arg', 'step', self.__step)
        self.__chip.set('arg', 'index', self.__index)

        # Setup journaling
        self.__chip.schema = JournalingSchema(self.__chip.schema)
        self.__chip.schema.start_journal()

        self.__setupSchemaAccess()

        # Make record of sc version and machine
        self.__record.record_version(self.__step, self.__index)

        # Record user information if enabled
        if self.__record_user_info:
            self.__record.record_userinformation(self.__step, self.__index)

        # Start wall timer
        self.__record.record_time(self.__step, self.__index, RecordTime.START)

        self.__task.setup_work_directory(self.__workdir)

        cwd = os.getcwd()
        os.chdir(self.__workdir)

        self.__chip._add_file_logger(self.__logs["sc"])

        try:
            _setupnode(chip, flow, step, index, replay)

            self.execute()
        except Exception as e:
            utils.print_traceback(chip.logger, e)
            _haltstep(chip, chip.get('option', 'flow'), step, index)

        # return to original directory
        os.chdir(cwd)

        # Stop journaling
        self.__chip.schema.stop_journal()
        self.__chip.schema = self.__chip.schema.get_base_schema()

        if self.__pipe:
            self.__pipe.send(self.__chip._packages)

    def execute(self):
        self.__task.set_runtime(self.__chip, step=self.__step, index=self.__index)

        self.logger.info(f'Running in {self.__workdir}')

        try:
            self.__task.pre_process()
        except Exception as e:
            self.logger.error(
                f"Pre-processing failed for {self.__task.name()}/{self.__task.task()}")
            utils.print_traceback(self.logger, e)
            raise e

        if self.__record.get('status', step=self.__step, index=self.__index) == NodeStatus.SKIPPED:
            # copy inputs to outputs and skip execution
            forward_output_files(chip, step, index)

            send_messages.send(self.__chip, "skipped", self.__step, self.__index)
        else:
            org_env = os.environ.copy()
            os.environ.update(self.__task.get_runtime_environmental_variables())

            toolpath = self.__task.get_exe()
            version = self.__task.get_exe_version()

            if not self.__chip.get('option', 'novercheck', step=self.__step, index=self.__index):
                if not self.__task.check_exe_version(version):
                    self.halt()

            if version:
                self.__record.record_tool(self.__step, self.__index, version, RecordTool.VERSION)

            if toolpath:
                self.__record.record_tool(self.__step, self.__index, toolpath, RecordTool.PATH)

            send_messages.send(self.__chip, "begin", self.__step, self.__index)

            try:
                self.__task.generate_replay_script(self.__replay, self.__workdir)
                ret_code = self.__task.run_task(
                    self.__workdir,
                    self.__chip.get('option', 'quiet', step=self.__step, index=self.__index),
                    self.__chip.get('option', 'loglevel', step=self.__step, index=self.__index),
                    self.__chip.get('option', 'breakpoint', step=self.__step, index=self.__index),
                    self.__chip.get('option', 'nice', step=self.__step, index=self.__index),
                    self.__chip.get('option', 'timeout', step=self.__step, index=self.__index))
            except Exception as e:
                raise e

            os.environ.clear()
            os.environ.update(org_env)

            if ret_code != 0:
                msg = f'Command failed with code {ret_code}.'
                if os.path.exists(self.__logs["exe"]):
                    if self.__chip.get('option', 'quiet', step=self.__step, index=self.__index):
                        # Print last N lines of log when in quiet mode
                        with sc_open(self.__logs["exe"]) as logfd:
                            loglines = logfd.read().splitlines()
                            for logline in loglines[-self.__failed_log_lines:]:
                                self.logger.error(logline)
                        # No log file for pure-Python tools.
                    msg += f' See log file {os.path.abspath(self.__logs["exe"])}'
                self.logger.warning(msg)
                self.__error = True

            try:
                self.__task.post_process()
            except Exception as e:
                self.logger.error(
                    f"Post-processing failed for {self.__task.name()}/{self.__task.task()}")
                utils.print_traceback(self.logger, e)
                self.__error = True

        _finalizenode(chip, step, index, replay)

        send_messages.send(self.__chip, "end", self.__step, self.__index)
