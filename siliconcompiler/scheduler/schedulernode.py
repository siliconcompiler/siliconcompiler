import contextlib
import logging
import os
import shutil
import sys
import time

import os.path

from logging.handlers import QueueHandler

from siliconcompiler import utils, sc_open
from siliconcompiler import Schema
from siliconcompiler import NodeStatus
from siliconcompiler.utils.logging import get_console_formatter, SCInRunLoggerFormatter
from siliconcompiler.schema import utils as schema_utils

from siliconcompiler.tools._common import input_file_node_name, record_metric

from siliconcompiler.record import RecordTime, RecordTool
from siliconcompiler.schema import Journal
from siliconcompiler.scheduler import send_messages


class SchedulerNode:
    def __init__(self, chip, step, index, replay=False):
        self.__step = step
        self.__index = index
        self.__chip = chip

        self.__design = self.__chip.design

        self.__job = self.__chip.get('option', 'jobname')
        self.__record_user_info = self.__chip.get("option", "track",
                                                  step=self.__step, index=self.__index)
        self.__pipe = None
        self.__failed_log_lines = 20
        self.__error = False
        self.__generate_test_case = not replay
        self.__replay = replay
        self.__hash = self.__chip.get("option", "hash")
        self.__builtin = False

        self.__enforce_inputfiles = self.__chip.get('option', 'strict')
        self.__enforce_outputfiles = self.__chip.get('option', 'strict')

        flow = self.__chip.get('option', 'flow')
        self.__is_entry_node = (self.__step, self.__index) in \
            self.__chip.get("flowgraph", flow, field="schema").get_entry_nodes()

        self.__jobworkdir = self.__chip.getworkdir(jobname=self.__job)
        self.__workdir = self.__chip.getworkdir(jobname=self.__job,
                                                step=self.__step, index=self.__index)
        self.__manifests = {
            "input": os.path.join(self.__workdir, "inputs", f"{self.__design}.pkg.json"),
            "output": os.path.join(self.__workdir, "outputs", f"{self.__design}.pkg.json")
        }
        self.__logs = {
            "sc": os.path.join(self.__workdir, f"sc_{self.__step}_{self.__index}.log"),
            "exe": os.path.join(self.__workdir, f"{self.__step}.log")
        }
        self.__replay_script = os.path.join(self.__workdir, "replay.sh")

        self.set_queue(None, None)
        self.__setup_schema_access()

    @contextlib.contextmanager
    def runtime(self):
        prev_task = self.__task
        with self.__task.runtime(self.__chip, step=self.__step, index=self.__index) as runtask:
            self.__task = runtask
            yield
        self.__task = prev_task

    @staticmethod
    def init(chip):
        pass

    @property
    def is_local(self):
        return True

    @property
    def has_error(self):
        return self.__error

    def set_builtin(self):
        self.__builtin = True

    @property
    def is_builtin(self):
        return self.__builtin

    @property
    def logger(self):
        return self.__chip.logger

    @property
    def chip(self):
        return self.__chip

    @property
    def step(self):
        return self.__step

    @property
    def index(self):
        return self.__index

    @property
    def design(self):
        return self.__design

    @property
    def workdir(self):
        return self.__workdir

    @property
    def jobworkdir(self):
        return self.__jobworkdir

    @property
    def is_replay(self):
        return self.__replay

    @property
    def task(self):
        return self.__task

    def get_manifest(self, input=False):
        if input:
            return self.__manifests["input"]
        return self.__manifests["output"]

    def get_log(self, type="exe"):
        if type not in self.__logs:
            raise ValueError(f"{type} is not a log")
        return self.__logs[type]

    @property
    def replay_script(self):
        return self.__replay_script

    @property
    def threads(self):
        with self.__task.runtime(self.__chip, step=self.__step, index=self.__index) as task:
            thread_count = task.get("threads")
        return thread_count

    def set_queue(self, pipe, queue):
        self.__pipe = pipe
        self.__queue = queue

        # Reinit
        self.__setup_schema_access()

    def __setup_schema_access(self):
        flow = self.__chip.get('option', 'flow')
        self.__flow = self.__chip.get("flowgraph", flow, field="schema")

        tool = self.__flow.get(self.__step, self.__index, 'tool')
        task = self.__flow.get(self.__step, self.__index, 'task')
        self.__task = self.__chip.get("tool", tool, "task", task, field="schema")
        self.__record = self.__chip.get("record", field="schema")
        self.__metrics = self.__chip.get("metric", field="schema")

    def _init_run_logger(self):
        self.__chip._logger_console.setFormatter(
            get_console_formatter(self.__chip, True, self.__step, self.__index))
        self.logger.setLevel(
            schema_utils.translate_loglevel(self.__chip.get('option', 'loglevel',
                                            step=self.__step, index=self.__index)))

        if self.__queue:
            formatter = self.__chip._logger_console.formatter
            self.logger.removeHandler(self.__chip._logger_console)
            self.__chip._logger_console = QueueHandler(self.__queue)
            self.__chip._logger_console.setFormatter(formatter)
            self.logger.addHandler(self.__chip._logger_console)

    def halt(self, msg=None):
        if msg:
            self.logger.error(msg)

        self.__record.set("status", NodeStatus.ERROR, step=self.__step, index=self.__index)
        try:
            self.__chip.schema.write_manifest(self.__manifests["output"])
        except FileNotFoundError:
            self.logger.error(f"Failed to write manifest for {self.__step}/{self.__index}.")

        self.logger.error(f"Halting {self.__step}/{self.__index} due to errors.")
        send_messages.send(self.__chip, "fail", self.__step, self.__index)
        sys.exit(1)

    def setup(self):
        with self.__task.runtime(self.__chip, step=self.__step, index=self.__index) as task:
            # Run node setup.
            self.logger.info(f'Setting up node {self.__step}/{self.__index} with '
                             f'{task.tool()}/{task.task()}')
            setup_ret = None
            try:
                setup_ret = task.setup()
            except Exception as e:
                self.logger.error(f'Failed to run setup() for {self.__step}/{self.__index} '
                                  f'with {task.tool()}/{task.task()}')
                raise e

            if setup_ret is not None:
                self.logger.warning(f'Removing {self.__step}/{self.__index} due to {setup_ret}')
                self.__record.set('status', NodeStatus.SKIPPED,
                                  step=self.__step, index=self.__index)

                return False

            return True

    def check_previous_run_status(self, previous_run):
        # Assume modified if flow does not match
        if self.__flow.name() != previous_run.__flow.name():
            self.logger.debug("Flow name changed")
            return False

        # Tool name
        if self.__task.tool() != previous_run.__task.tool():
            self.logger.debug("Tool name changed")
            return False

        # Task name
        if self.__task.task() != previous_run.__task.task():
            self.logger.debug("Task name changed")
            return False

        previous_status = previous_run.__chip.get("record", "status",
                                                  step=self.__step, index=self.__index)
        if not NodeStatus.is_done(previous_status):
            self.logger.debug("Previous step did not complete")
            # Not complete
            return False

        if not NodeStatus.is_success(previous_status):
            self.logger.debug("Previous step was not successful")
            # Not a success
            return False

        # Check input nodes
        log_level = self.logger.level
        self.logger.setLevel(logging.CRITICAL)
        sel_inputs = self.__task.select_input_nodes()
        self.logger.setLevel(log_level)
        if set(previous_run.__chip.get("record", "inputnode",
                                       step=self.__step, index=self.__index)) != set(sel_inputs):
            self.logger.warning(f'inputs to {self.__step}/{self.__index} has been modified from '
                                'previous run')
            return False

        # Check that all output files are present?

        return True

    def check_values_changed(self, previous_run, keys):
        def print_warning(key):
            self.logger.warning(f'[{",".join(key)}] in {self.__step}/{self.__index} has been '
                                'modified from previous run')

        for key in sorted(keys):
            if not self.__chip.valid(*key) or not previous_run.__chip.valid(*key):
                # Key is missing in either run
                print_warning(key)
                return True

            param = self.__chip.get(*key, field=None)
            step, index = self.__step, self.__index
            if param.get(field='pernode').is_never():
                step, index = None, None

            check_val = param.get(step=step, index=index)
            prev_val = previous_run.__chip.get(*key, step=step, index=index)

            if check_val != prev_val:
                print_warning(key)
                return True

        return False

    def check_files_changed(self, previous_run, previous_time, keys):
        use_hash = self.__hash and previous_run.__hash

        def print_warning(key, reason):
            self.logger.warning(f'[{",".join(key)}] ({reason}) in {self.__step}/{self.__index} has '
                                'been modified from previous run')

        def get_file_time(path):
            times = [os.path.getmtime(path)]
            if os.path.isdir(path):
                for path_root, _, files in os.walk(path):
                    for path_end in files:
                        times.append(os.path.getmtime(os.path.join(path_root, path_end)))

            return max(times)

        for key in sorted(keys):
            param = self.__chip.get(*key, field=None)
            step, index = self.__step, self.__index
            if param.get(field='pernode').is_never():
                step, index = None, None

            if use_hash:
                check_hash = self.__chip.hash_files(*key, update=False, check=False,
                                                    verbose=False, allow_cache=True,
                                                    step=step, index=index)
                prev_hash = previous_run.__chip.get(*key, field='filehash',
                                                    step=step, index=index)

                if check_hash != prev_hash:
                    print_warning(key, "file hash")
                    return True
            else:
                # check package values
                check_val = self.__chip.get(*key, field='package', step=step, index=index)
                prev_val = previous_run.__chip.get(*key, field='package', step=step, index=index)

                if check_val != prev_val:
                    print_warning(key, "file package")
                    return True

                for check_file in self.__chip.find_files(*key, step=step, index=index):
                    if get_file_time(check_file) > previous_time:
                        print_warning(key, "timestamp")
                        return True

        return False

    def get_check_changed_keys(self):
        all_keys = set()

        all_keys.update(self.__task.get('require'))

        tool_task_prefix = ('tool', self.__task.tool(), 'task', self.__task.task())
        for key in ('option', 'threads', 'prescript', 'postscript', 'refdir', 'script',):
            all_keys.add(",".join([*tool_task_prefix, key]))

        for env_key in self.__chip.getkeys(*tool_task_prefix, 'env'):
            all_keys.add(",".join([*tool_task_prefix, 'env', env_key]))

        value_keys = set()
        path_keys = set()
        for key in all_keys:
            keypath = tuple(key.split(","))
            if not self.__chip.valid(*keypath, default_valid=True):
                raise KeyError(f"[{','.join(keypath)}] not found")
            keytype = self.__chip.get(*keypath, field="type")
            if 'file' in keytype or 'dir' in keytype:
                path_keys.add(keypath)
            else:
                value_keys.add(keypath)

        return value_keys, path_keys

    def requires_run(self):
        from siliconcompiler import Chip

        # Load previous manifest
        previous_node = None
        previous_node_time = time.time()
        if os.path.exists(self.__manifests["input"]):
            previous_node_time = os.path.getmtime(self.__manifests["input"])
            chip = Chip('')
            try:
                chip.schema = Schema(manifest=self.__manifests["input"], logger=self.logger)
            except:  # noqa E722
                self.logger.debug("Input manifest failed to load")
                return True
            previous_node = SchedulerNode(chip, self.__step, self.__index)
        else:
            # No manifest found so assume rerun is needed
            self.logger.debug("Previous run did not generate input manifest")
            return True

        previous_node_end = None
        if os.path.exists(self.__manifests["output"]):
            chip = Chip('')
            try:
                chip.schema = Schema(manifest=self.__manifests["output"], logger=self.logger)
            except:  # noqa E722
                self.logger.debug("Output manifest failed to load")
                return True
            previous_node_end = SchedulerNode(chip, self.__step, self.__index)
        else:
            # No manifest found so assume rerun is needed
            self.logger.debug("Previous run did not generate output manifest")
            return True

        with self.runtime():
            if previous_node_end:
                with previous_node_end.runtime():
                    if not self.check_previous_run_status(previous_node_end):
                        self.logger.debug("Previous run state failed")
                        return True

            if previous_node:
                with previous_node.runtime():
                    # Generate key paths to check
                    try:
                        value_keys, path_keys = self.get_check_changed_keys()
                        previous_value_keys, previous_path_keys = \
                            previous_node.get_check_changed_keys()
                        value_keys.update(previous_value_keys)
                        path_keys.update(previous_path_keys)
                    except KeyError:
                        self.logger.debug("Failed to acquire keys")
                        return True

                    if self.check_values_changed(previous_node, value_keys.union(path_keys)):
                        self.logger.debug("Key values changed")
                        return True

                    if self.check_files_changed(previous_node, previous_node_time, path_keys):
                        self.logger.debug("Files changed")
                        return True

        return False

    def setup_input_directory(self):
        in_files = set(self.__task.get('input'))

        for in_step, in_index in self.__record.get('inputnode',
                                                   step=self.__step, index=self.__index):
            if NodeStatus.is_error(self.__record.get('status', step=in_step, index=in_index)):
                self.halt(f'Halting step due to previous error in {in_step}/{in_index}')

            output_dir = os.path.join(
                self.__chip.getworkdir(step=in_step, index=in_index), "outputs")
            if not os.path.isdir(output_dir):
                self.halt(f'Unable to locate outputs directory for {in_step}/{in_index}: '
                          f'{output_dir}')

            for outfile in os.scandir(output_dir):
                if outfile.name == f'{self.__design}.pkg.json':
                    # Dont forward manifest
                    continue

                new_name = input_file_node_name(outfile.name, in_step, in_index)
                if self.__enforce_inputfiles:
                    if outfile.name not in in_files and new_name not in in_files:
                        continue

                if outfile.is_file() or outfile.is_symlink():
                    utils.link_symlink_copy(outfile.path,
                                            f'{self.__workdir}/inputs/{outfile.name}')
                elif outfile.is_dir():
                    shutil.copytree(outfile.path,
                                    f'{self.__workdir}/inputs/{outfile.name}',
                                    dirs_exist_ok=True,
                                    copy_function=utils.link_symlink_copy)

                if new_name in in_files:
                    # perform rename
                    os.rename(f'{self.__workdir}/inputs/{outfile.name}',
                              f'{self.__workdir}/inputs/{new_name}')

    def validate(self):
        '''
        Runtime checks called from _runtask().

        - Make sure expected inputs exist.
        - Make sure all required filepaths resolve correctly.
        '''
        error = False

        required_inputs = self.__task.get('input')

        input_dir = os.path.join(self.__workdir, 'inputs')

        for filename in required_inputs:
            path = os.path.join(input_dir, filename)
            if not os.path.exists(path):
                self.logger.error(f'Required input {filename} not received for '
                                  f'{self.__step}/{self.__index}.')
                error = True

        all_required = self.__task.get('require')
        for item in all_required:
            keypath = item.split(',')
            if not self.__chip.valid(*keypath):
                self.logger.error(f'Cannot resolve required keypath [{",".join(keypath)}].')
                error = True
                continue

            param = self.__chip.get(*keypath, field=None)
            check_step, check_index = self.__step, self.__index
            if param.get(field='pernode').is_never():
                check_step, check_index = None, None

            value = self.__chip.get(*keypath, step=check_step, index=check_index)
            if not value:
                self.logger.error('No value set for required keypath '
                                  f'[{",".join(keypath)}].')
                error = True
                continue

            paramtype = param.get(field='type')
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

        walltime = self.__metrics.get("tasktime", step=self.__step, index=self.__index)
        self.logger.info(f"Finished task in {walltime:.2f}s")

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

        # Setup logger
        self._init_run_logger()

        self.__chip.set('arg', 'step', self.__step)
        self.__chip.set('arg', 'index', self.__index)

        # Setup journaling
        journal = Journal.access(self.__chip.schema)
        journal.start()

        # Must be after journaling to ensure journal is complete
        self.__setup_schema_access()

        # Make record of sc version and machine
        self.__record.record_version(self.__step, self.__index)

        # Record user information if enabled
        if self.__record_user_info:
            self.__record.record_userinformation(self.__step, self.__index)

        # Start wall timer
        self.__record.record_time(self.__step, self.__index, RecordTime.START)

        cwd = os.getcwd()
        with self.runtime():
            # Setup run directory
            self.__task.setup_work_directory(self.__workdir, remove_exist=not self.__replay)

            os.chdir(self.__workdir)

            # Attach siliconcompiler file log handler
            file_log = logging.FileHandler(self.__logs["sc"])
            file_log.setFormatter(
                SCInRunLoggerFormatter(self.__chip, self.__job, self.__step, self.__index))
            self.logger.addHandler(file_log)

            # Select the inputs to this node
            sel_inputs = self.__task.select_input_nodes()
            if not self.__is_entry_node and not sel_inputs:
                self.halt(f'No inputs selected for {self.__step}/{self.__index}')
            self.__record.set("inputnode", sel_inputs, step=self.__step, index=self.__index)

            if self.__hash:
                self.__hash_files_pre_execute()

            # Forward data
            if not self.__replay:
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
        journal.stop()

        if self.__pipe:
            self.__pipe.send(self.__chip.get("package", field="schema").get_path_cache())

    def execute(self):
        self.logger.info(f'Running in {self.__workdir}')

        try:
            self.__task.pre_process()
        except Exception as e:
            self.logger.error(
                f"Pre-processing failed for {self.__task.tool()}/{self.__task.task()}")
            utils.print_traceback(self.logger, e)
            raise e

        if self.__record.get('status', step=self.__step, index=self.__index) == NodeStatus.SKIPPED:
            # copy inputs to outputs and skip execution
            for in_step, in_index in self.__record.get('inputnode',
                                                       step=self.__step, index=self.__index):
                required_outputs = set(self.__task.get('output'))
                in_workdir = self.__chip.getworkdir(step=in_step, index=in_index)
                for outfile in os.scandir(f"{in_workdir}/outputs"):
                    if outfile.name == f'{self.__design}.pkg.json':
                        # Dont forward manifest
                        continue

                    if outfile.name not in required_outputs:
                        # Dont forward non-required outputs
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
                if not self.__replay:
                    self.__task.generate_replay_script(self.__replay_script, self.__workdir)
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
                    f"Post-processing failed for {self.__task.tool()}/{self.__task.task()}")
                utils.print_traceback(self.logger, e)
                self.__error = True

        self.check_logfile()

        if not self.__error and self.__hash:
            self.__hash_files_post_execute()

        # Capture wall runtime
        self.__record.record_time(self.__step, self.__index, RecordTime.END)
        self.__metrics.record_tasktime(self.__step, self.__index, self.__record)
        self.__metrics.record_totaltime(
            self.__step, self.__index,
            self.__flow,
            self.__record)

        # Save a successful manifest
        if self.__record.get('status', step=self.__step, index=self.__index) != NodeStatus.SKIPPED:
            self.__record.set('status', NodeStatus.SUCCESS, step=self.__step, index=self.__index)

        self.__chip.write_manifest(self.__manifests["output"])

        self.summarize()

        if self.__error and self.__generate_test_case:
            self.__generate_testcase()

        # Stop if there are errors
        errors = self.__metrics.get('errors', step=self.__step, index=self.__index)
        if errors and not self.__chip.get('option', 'continue',
                                          step=self.__step, index=self.__index):
            self.halt(f'{self.__task.tool()}/{self.__task.task()} reported {errors} '
                      f'errors during {self.__step}/{self.__index}')

        if self.__error:
            self.halt()

        self.__report_output_files()

        send_messages.send(self.__chip, "end", self.__step, self.__index)

    def __generate_testcase(self):
        from siliconcompiler.utils.issue import generate_testcase
        import lambdapdk

        generate_testcase(
            self.__chip,
            self.__step,
            self.__index,
            archive_directory=self.__jobworkdir,
            include_pdks=False,
            include_specific_pdks=lambdapdk.get_pdks(),
            include_libraries=False,
            include_specific_libraries=lambdapdk.get_libs(),
            hash_files=self.__hash,
            verbose_collect=False)

    def check_logfile(self):
        if self.__record.get('status', step=self.__step, index=self.__index) == NodeStatus.SKIPPED:
            return

        checks = {}
        matches = {}
        for suffix in self.__task.getkeys('regex'):
            regexes = self.__task.get('regex', suffix)
            if not regexes:
                continue

            checks[suffix] = {
                "report": open(f"{self.__step}.{suffix}", "w"),
                "args": regexes,
                "display": False
            }
            matches[suffix] = 0

        def print_error(suffix, line):
            self.logger.error(line)

        def print_warning(suffix, line):
            self.logger.warning(line)

        def print_info(suffix, line):
            self.logger.warning(f'{suffix}: {line}')

        if not self.__chip.get('option', 'quiet', step=self.__step, index=self.__index):
            for suffix, info in checks.items():
                if suffix == 'errors':
                    info["display"] = print_error
                elif suffix == "warnings":
                    info["display"] = print_warning
                else:
                    info["display"] = print_info

        # Order suffixes as follows: [..., 'warnings', 'errors']
        ordered_suffixes = list(
            filter(lambda key: key not in ['warnings', 'errors'], checks.keys()))
        if 'warnings' in checks:
            ordered_suffixes.append('warnings')
        if 'errors' in checks:
            ordered_suffixes.append('errors')

        # Looping through patterns for each line
        with sc_open(self.__logs["exe"]) as f:
            line_count = sum(1 for _ in f)
            right_align = len(str(line_count))
            for suffix in ordered_suffixes:
                # Start at the beginning of file again
                f.seek(0)
                for num, line in enumerate(f, start=1):
                    string = line
                    for item in checks[suffix]['args']:
                        if string is None:
                            break
                        else:
                            string = utils.grep(self.__chip, item, string)
                    if string is not None:
                        matches[suffix] += 1
                        # always print to file
                        line_with_num = f'{num: >{right_align}}: {string.strip()}'
                        print(line_with_num, file=checks[suffix]['report'])
                        # selectively print to display
                        if checks[suffix]["display"]:
                            checks[suffix]["display"](suffix, line_with_num)

        for check in checks.values():
            check['report'].close()

        for metric in ("errors", "warnings"):
            if metric in matches:
                errors = self.__metrics.get(metric, step=self.__step, index=self.__index)
                if errors is None:
                    errors = 0
                errors += matches[metric]

                sources = [os.path.basename(self.__logs["exe"])]
                if self.__task.get('regex', metric):
                    sources.append(f'{self.__step}.{metric}')

                record_metric(self.__chip, self.__step, self.__index, metric, errors, sources)

    def __hash_files_pre_execute(self):
        for task_key in ('refdir', 'prescript', 'postscript', 'script'):
            self.__chip.hash_files('tool', self.__task.tool(), 'task', self.__task.task(), task_key,
                                   step=self.__step, index=self.__index, check=False,
                                   allow_cache=True, verbose=False)

        # hash all requirements
        for item in set(self.__task.get('require')):
            args = item.split(',')
            sc_type = self.__chip.get(*args, field='type')
            if 'file' in sc_type or 'dir' in sc_type:
                access_step, access_index = self.__step, self.__index
                if self.__chip.get(*args, field='pernode').is_never():
                    access_step, access_index = None, None
                self.__chip.hash_files(*args, step=access_step, index=access_index,
                                       check=False, allow_cache=True, verbose=False)

    def __hash_files_post_execute(self):
        # hash all outputs
        self.__chip.hash_files('tool', self.__task.tool(), 'task', self.__task.task(), 'output',
                               step=self.__step, index=self.__index, check=False, verbose=False)

        # hash all requirements
        for item in set(self.__task.get('require')):
            args = item.split(',')
            sc_type = self.__chip.get(*args, field='type')
            if 'file' in sc_type or 'dir' in sc_type:
                access_step, access_index = self.__step, self.__index
                if self.__chip.get(*args, field='pernode').is_never():
                    access_step, access_index = None, None
                if self.__chip.get(*args, field='filehash'):
                    continue
                self.__chip.hash_files(*args, step=access_step, index=access_index,
                                       check=False, allow_cache=True, verbose=False)

    def __report_output_files(self):
        if self.__task.tool() == 'builtin':
            return

        error = False

        try:
            outputs = os.listdir(os.path.join(self.__workdir, "outputs"))
        except FileNotFoundError:
            self.halt("Output directory is missing")

        try:
            outputs.remove(os.path.basename(self.__manifests["output"]))
        except ValueError:
            self.logger.error(f"Output manifest ({os.path.basename(self.__manifests['output'])}) "
                              "is missing.")
            error = True

        outputs = set(outputs)

        output_files = set(self.__task.get('output'))

        missing = output_files.difference(outputs)
        excess = outputs.difference(output_files)

        if missing:
            error = True
            self.logger.error(f"Expected output files are missing: {', '.join(missing)}")

        if excess:
            error = True
            self.logger.error(f"Unexpected output files found: {', '.join(excess)}")

        if error and self.__enforce_outputfiles:
            self.halt()

    def copy_from(self, source):
        copy_from = self.__chip.getworkdir(jobname=source, step=self.__step, index=self.__index)

        if not os.path.exists(copy_from):
            return

        self.logger.info(f'Importing {self.__step}/{self.__index} from {source}')
        shutil.copytree(
            copy_from, self.__workdir,
            dirs_exist_ok=True,
            copy_function=utils.link_copy)

        # rewrite replay files
        if os.path.exists(self.__replay_script):
            # delete file as it might be a hard link
            os.remove(self.__replay_script)

            with self.runtime():
                self.__task.generate_replay_script(self.__replay_script, self.__workdir)

        for manifest in self.__manifests.values():
            if os.path.exists(manifest):
                schema = Schema.from_manifest(manifest)
                # delete file as it might be a hard link
                os.remove(manifest)
                schema.set('option', 'jobname', self.__chip.get('option', 'jobname'))
                schema.write_manifest(manifest)

    def clean_directory(self):
        if os.path.exists(self.__workdir):
            shutil.rmtree(self.__workdir)
