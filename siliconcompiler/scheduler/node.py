import os
import shutil
import sys

import os.path

from logging.handlers import QueueHandler

from siliconcompiler import utils, sc_open
from siliconcompiler import Schema
from siliconcompiler import NodeStatus

from siliconcompiler.tools._common import input_file_node_name

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

        flow = self.__chip.get('option', 'flow')
        self.__is_entry_node = (self.__step, self.__index) not in \
            self.__chip.get("flowgraph", flow, field="schema").get_entry_nodes()

        self.__workdir = self.__chip.getworkdir(jobname=self.__job,
                                                step=self.__step, index=self.__index)
        self.__manifests = {
            "input": os.path.join(self.__workdir, "inputs", f"{self.__design}.pkg.json"),
            "output": os.path.join(self.__workdir, "outputs", f"{self.__design}.pkg.json")
        }
        self.__logs = {
            "sc": os.path.join(self.__workdir, f"sc_{self.__step}{self.__index}.log"),
            "exe": os.path.join(self.__workdir, f"{self.__step}.log")
        }
        self.__replay = os.path.join(self.__workdir, "replay.sh")

        self.set_queue(None)
        self.__setup_schema_access()

    @property
    def logger(self):
        return self.__chip.logger

    def set_queue(self, queue):
        self.__queue = queue

    def __setup_schema_access(self):
        flow = self.__chip.get('option', 'flow')
        tool = self.__chip.get('flowgraph', flow, self.__step, self.__index, 'tool')

        self.__task = self.__chip.schema.get("tool", tool, field="schema")
        self.__record = self.__chip.schema.get("record", field="schema")
        self.__metrics = self.__chip.schema.get("record", field="schema")

    def halt(self, msg=None):
        if msg:
            self.logger.error(msg)

        self.__record.set("status", NodeStatus.ERROR, step=self.__step, index=self.__index)
        self.__chip.schema.write_manifest(self.__manifests["output"])

        self.logger.error(f"Halting {self.__step}{self.__index} due to errors.")
        send_messages.send(self.__chip, "fail", self.__step, self.__index)
        sys.exit(1)

    def setup(self):
        pass

    def requires_run(self):
        return True

    def setup_input_directory(self):
        strict = self.__chip.get('option', 'strict')

        in_files = set(self.__task.get('task', self.__task.task(), 'input',
                                       step=self.__step, index=self.__index))

        for in_step, in_index in self.__record.get('inputnode',
                                                   step=self.__step, index=self.__index):
            if self.__record('status', step=in_step, index=in_index) == NodeStatus.ERROR:
                self.halt(f'Halting step due to previous error in {in_step}{in_index}')

            output_dir = os.path.join(
                self.__chip.getworkdir(step=in_step, index=in_index), "outputs")
            if not os.path.isdir(output_dir):
                self.halt(f'Unable to locate outputs directory for {in_step}{in_index}: '
                          f'{output_dir}')

            for outfile in os.scandir(output_dir):
                if outfile.name == f'{self.__design}.pkg.json':
                    # Dont forward manifest
                    continue

                new_name = input_file_node_name(outfile.name, in_step, in_index)
                if strict:
                    if outfile.name not in in_files and new_name not in in_files:
                        continue

                if outfile.is_file() or outfile.is_symlink():
                    utils.link_symlink_copy(outfile.path,
                                            f'inputs/{outfile.name}')
                elif outfile.is_dir():
                    shutil.copytree(outfile.path,
                                    f'inputs/{outfile.name}',
                                    dirs_exist_ok=True,
                                    copy_function=utils.link_symlink_copy)

                if new_name in in_files:
                    # perform rename
                    os.rename(f'inputs/{outfile.name}', f'inputs/{new_name}')

    def validate(self):
        '''
        Runtime checks called from _runtask().

        - Make sure expected inputs exist.
        - Make sure all required filepaths resolve correctly.
        '''
        error = False

        required_inputs = self.__task.get('task', self.__task.task(), 'input',
                                          step=self.__step, index=self.__index)

        input_dir = os.path.join(self.__workdir, 'inputs')

        for filename in required_inputs:
            path = os.path.join(input_dir, filename)
            if not os.path.exists(path):
                self.logger.error(f'Required input {filename} not received for '
                                  f'{self.__step}{self.__index}.')
                error = True

        all_required = self.__task.get('task', self.__task.task(), 'require',
                                       step=self.__step, index=self.__index)
        for item in all_required:
            keypath = item.split(',')
            if not self.__chip.valid(*keypath):
                self.__chip.logger.error(f'Cannot resolve required keypath [{",".join(keypath)}].')
                error = True
                continue

            param = self.__chip.get(*keypath, field=None)
            check_step, check_index = self.__step, self.__index
            if param.get(field='pernode').is_never():
                check_step, check_index = Schema.GLOBAL_KEY, Schema.GLOBAL_KEY

            paramtype = param.get(field='type')

            value = self.__chip.get(*keypath, step=check_step, index=check_index)
            if not value:
                self.__chip.logger.error('No value set for required keypath '
                                         f'[{",".join(keypath)}].')
                error = True
                continue

            if ('file' in paramtype) or ('dir' in paramtype):
                abspath = self.__chip.find_files(*keypath,
                                                 missing_ok=True,
                                                 step=check_step, index=check_index)

                unresolved_paths = value
                if not isinstance(abspath, list):
                    abspath = [abspath]
                    unresolved_paths = [unresolved_paths]

                for path, setpath in zip(abspath, unresolved_paths):
                    if path is None:
                        self.logger.error(f'Cannot resolve path {setpath} in '
                                          f'required file keypath [{",".join(keypath)}].')
                        error = True

        return not error

    def summarize(self):
        for metric in ['errors', 'warnings']:
            val = self.__metrics.get(metric, step=self.__step, index=self.__index)
            if val is not None:
                self.logger.info(f'Number of {metric}: {val}')

        walltime = self.__record.get("tasktime", step=self.__step, index=self.__index)
        self.logger.info(f"Finished task in {round(walltime, 2)}s")

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

        # Must be after journaling to ensure journal is complete
        self.__setup_schema_access()

        # Make record of sc version and machine
        self.__record.record_version(self.__step, self.__index)

        # Record user information if enabled
        if self.__record_user_info:
            self.__record.record_userinformation(self.__step, self.__index)

        # Start wall timer
        self.__record.record_time(self.__step, self.__index, RecordTime.START)

        # Setup run directory
        self.__task.setup_work_directory(self.__workdir)

        cwd = os.getcwd()
        os.chdir(self.__workdir)

        # Attach siliconcompiler file log handler
        self.__chip._add_file_logger(self.__logs["sc"])

        # Select the inputs to this node
        sel_inputs = self.__task.select_input_nodes()
        if not self.__is_entry_node and not sel_inputs:
            self.halt(f'No inputs selected for {self.__step}{self.__index}')

        _hash_files(chip, step, index, setup=True)

        # Forward data
        self.setup_input_directory()

        # Write manifest prior to step running into inputs
        self.__chip.write_manifest(self.__manifests["input"])

        # Check manifest
        if not self.validate():
            self.halt("Failed to validate node setup. See previous errors")

        try:
            self.execute()
        except Exception as e:
            utils.print_traceback(self.logger, e)
            self.halt()

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
            for in_step, in_index in self.__record('inputnode',
                                                   step=self.__step, index=self.__index):
                in_workdir = self.__chip.getworkdir(step=in_step, index=in_index)
                for outfile in os.scandir(f"{in_workdir}/outputs"):
                    if outfile.name == f'{self.__design}.pkg.json':
                        # Dont forward manifest
                        continue

                    if outfile.is_file() or outfile.is_symlink():
                        utils.link_symlink_copy(outfile.path,
                                                f'outputs/{outfile.name}')
                    elif outfile.is_dir():
                        shutil.copytree(outfile.path,
                                        f'outputs/{outfile.name}',
                                        dirs_exist_ok=True,
                                        copy_function=utils.link_symlink_copy)

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

        flow = chip.get('option', 'flow')
        quiet = (
            chip.get('option', 'quiet', step=step, index=index) and not
            chip.get('option', 'breakpoint', step=step, index=index)
        )

        is_skipped = chip.get('record', 'status', step=step, index=index) == NodeStatus.SKIPPED

        if not is_skipped:
            _check_logfile(chip, step, index, quiet, None)

        _hash_files(chip, step, index)

        # Capture wall runtime
        self.__record.record_time(self.__step, self.__index, RecordTime.END)
        self.__record.record_totaltime(
            self.__step, self.__index,
            self.__chip.get("flowgraph", flow, field='schema'),
            self.__record)

        # Save a successful manifest
        if not is_skipped:
            self.__record.set('status', NodeStatus.SUCCESS, step=self.__step, index=self.__index)

        self.__chip.write_manifest(self.__manifests["output"])

        self.summarize()

        if self.__error and self.__generateTestCase:
            _make_testcase(chip, step, index)

        # Stop if there are errors
        errors = self.__metrics.get('errors', step=self.__step, index=self.__index)
        if errors and not self.__chip.get('option', 'continue',
                                          step=self.__step, index=self.__index):
            self.halt(f'{self.__task.name()}/{self.__task.task()} reported {errors} '
                      f'errors during {self.__step}{self.__index}')

        if self.__error:
            self.halt()

        if self.__chip.get('option', 'strict'):
            assert_output_files(chip, step, index)

        send_messages.send(self.__chip, "end", self.__step, self.__index)
