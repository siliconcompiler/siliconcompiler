import multiprocessing
import sys
import time

import os.path

from logging.handlers import QueueListener

from siliconcompiler import NodeStatus
from siliconcompiler import SiliconCompilerError
from siliconcompiler import utils
from siliconcompiler.flowgraph import RuntimeFlowgraph

from siliconcompiler.schema import Journal

from siliconcompiler.utils.logging import SCBlankLoggerFormatter


class TaskScheduler:
    __callbacks = {
        "pre_run": lambda chip: None,
        "pre_node": lambda chip, step, index: None,
        "post_node": lambda chip, step, index: None,
        "post_run": lambda chip: None,
    }

    @staticmethod
    def register_callback(hook, func):
        if hook not in TaskScheduler.__callbacks:
            raise ValueError(f"{hook} is not a valid callback")
        TaskScheduler.__callbacks[hook] = func

    def __init__(self, chip, tasks):
        self.__chip = chip
        self.__logger = self.__chip.logger
        self.__logger_console_handler = self.__chip._logger_console
        self.__schema = self.__chip.schema
        self.__flow = self.__schema.get("flowgraph", self.__chip.get('option', 'flow'),
                                        field="schema")
        self.__record = self.__schema.get("record", field="schema")
        self.__dashboard = chip._dash

        self.__max_cores = utils.get_cores(chip)
        self.__max_threads = utils.get_cores(chip)
        self.__max_parallel_run = self.__chip.get('option', 'scheduler', 'maxnodes')
        if not self.__max_parallel_run:
            self.__max_parallel_run = utils.get_cores(chip)
        # clip max parallel jobs to 1 <= jobs <= max_cores
        self.__max_parallel_run = max(1, min(self.__max_parallel_run, self.__max_cores))

        self.__runtime_flow = RuntimeFlowgraph(
            self.__flow,
            from_steps=self.__chip.get('option', 'from'),
            to_steps=self.__chip.get('option', 'to'),
            prune_nodes=self.__chip.get('option', 'prune'))

        self.__log_queue = multiprocessing.Queue(-1)

        self.__nodes = {}
        self.__startTimes = {}
        self.__dwellTime = 0.1

        self.__create_nodes(tasks)

    def __create_nodes(self, tasks):
        runtime = RuntimeFlowgraph(
            self.__flow,
            from_steps=set([step for step, _ in self.__flow.get_entry_nodes()]),
            prune_nodes=self.__chip.get('option', 'prune'))

        init_funcs = set()

        for step, index in self.__runtime_flow.get_nodes():
            if self.__record.get('status', step=step, index=index) != NodeStatus.PENDING:
                continue

            with tasks[(step, index)].runtime():
                threads = tasks[(step, index)].threads
            if not threads:
                threads = self.__max_threads
            threads = max(1, min(threads, self.__max_threads))

            task = {
                "name": f"{step}/{index}",
                "inputs": runtime.get_node_inputs(step, index, record=self.__record),
                "proc": None,
                "parent_pipe": None,
                "threads": threads,
                "running": False,
                "manifest": os.path.join(self.__chip.getworkdir(step=step, index=index),
                                         'outputs',
                                         f'{self.__chip.design}.pkg.json'),
                "node": tasks[(step, index)]
            }

            task["parent_pipe"], pipe = multiprocessing.Pipe()
            task["node"].set_queue(pipe, self.__log_queue)

            task["proc"] = multiprocessing.Process(target=task["node"].run)
            init_funcs.add(task["node"].init)
            self.__nodes[(step, index)] = task

        # Call preprocessing for schedulers
        for init_func in init_funcs:
            init_func(self.__chip)

    def run(self):
        # Call this in case this was invoked without __main__
        multiprocessing.freeze_support()

        # Handle logs across threads
        log_listener = QueueListener(self.__log_queue, self.__logger_console_handler)
        console_format = self.__logger_console_handler.formatter
        self.__logger_console_handler.setFormatter(SCBlankLoggerFormatter())
        log_listener.start()

        # Update dashboard before run begins
        if self.__dashboard:
            self.__dashboard.update_manifest()

        TaskScheduler.__callbacks["pre_run"](self.__chip)

        try:
            self.__run_loop()
        except KeyboardInterrupt:
            # exit immediately
            log_listener.stop()
            sys.exit(0)

        TaskScheduler.__callbacks["post_run"](self.__chip)

        # Cleanup logger
        log_listener.stop()
        self.__logger_console_handler.setFormatter(console_format)

    def __run_loop(self):
        self.__startTimes = {None: time.time()}

        while len(self.get_nodes_waiting_to_run()) > 0 or len(self.get_running_nodes()) > 0:
            changed = self.__process_completed_nodes()
            changed |= self.__lanuch_nodes()

            if changed and self.__dashboard:
                # Update dashboard if the manifest changed
                self.__dashboard.update_manifest(payload={"starttimes": self.__startTimes})

            running_nodes = self.get_running_nodes()

            # Check for situation where we have stuff left to run but don't
            # have any nodes running. This shouldn't happen, but we will get
            # stuck in an infinite loop if it does, so we want to break out
            # with an explicit error.
            if len(self.get_nodes_waiting_to_run()) > 0 and len(running_nodes) == 0:
                raise SiliconCompilerError(
                    'Nodes left to run, but no running nodes. From/to may be invalid.',
                    chip=self.__chip)

            if len(running_nodes) == 1:
                # if there is only one node running, just join the thread
                self.__nodes[running_nodes[0]]["proc"].join()
            elif len(running_nodes) > 1:
                # if there are more than 1, join the first with a timeout
                self.__nodes[running_nodes[0]]["proc"].join(timeout=self.__dwellTime)

    def get_nodes(self):
        return sorted(self.__nodes.keys())

    def get_running_nodes(self):
        nodes = []
        for node, info in self.__nodes.items():
            if info["running"]:
                nodes.append(node)
        return sorted(nodes)

    def get_nodes_waiting_to_run(self):
        nodes = []
        for node, info in self.__nodes.items():
            if not info["running"] and info["proc"]:
                nodes.append(node)
        return sorted(nodes)

    def __process_completed_nodes(self):
        changed = False
        for node in self.get_running_nodes():
            info = self.__nodes[node]

            if not info["proc"].is_alive():
                manifest = info["manifest"]

                self.__logger.debug(f'{info["name"]} is complete merging: {manifest}')

                if os.path.exists(manifest):
                    Journal.replay_file(self.__schema, manifest)
                    # TODO: once tool is fixed this can go away
                    self.__schema.unset("arg", "step")
                    self.__schema.unset("arg", "index")

                if info["parent_pipe"] and info["parent_pipe"].poll(1):
                    try:
                        packages = info["parent_pipe"].recv()
                        if isinstance(packages, dict):
                            for package, path in packages.items():
                                self.__chip.get("package", field="schema")._set_cache(package, path)
                    except:  # noqa E722
                        pass

                step, index = node
                if info["proc"].exitcode > 0:
                    status = NodeStatus.ERROR
                else:
                    status = self.__record.get('status', step=step, index=index)
                    if not status or status == NodeStatus.PENDING:
                        status = NodeStatus.ERROR

                self.__record.set('status', status, step=step, index=index)

                info["running"] = False
                info["proc"] = None

                changed = True

                TaskScheduler.__callbacks['post_node'](self.__chip, step, index)

        return changed

    def __allow_start(self, node):
        info = self.__nodes[node]

        if not info["node"].is_local:
            # using a different scheduler, so allow
            return True

        running_nodes = self.get_running_nodes()

        if len(running_nodes) >= self.__max_parallel_run:
            # exceeding machine resources
            return False

        current_threads = sum([self.__nodes[run_node]["threads"] for run_node in running_nodes])

        if info["threads"] + current_threads > self.__max_cores:
            # delay until there are enough core available
            return False

        # allow
        return True

    def __lanuch_nodes(self):
        changed = False
        for node in self.get_nodes_waiting_to_run():
            # TODO: breakpoint logic:
            # if node is breakpoint, then don't launch while len(running_nodes) > 0

            info = self.__nodes[node]
            step, index = node

            ready = True
            inputs = []
            for in_step, in_index in info["inputs"]:
                in_status = self.__record.get('status', step=in_step, index=in_index)
                inputs.append(in_status)

                if not NodeStatus.is_done(in_status):
                    ready = False
                    break
                if NodeStatus.is_error(in_status) and not info["node"].is_builtin:
                    # Fail if any dependency failed for non-builtin task
                    self.__record.set("status", NodeStatus.ERROR, step=step, index=index)

            # Fail if no dependency successfully finished for builtin task
            if inputs:
                any_success = any([status == NodeStatus.SUCCESS for status in inputs])
            else:
                any_success = True
            if ready and info["node"].is_builtin and not any_success:
                self.__record.set("status", NodeStatus.ERROR, step=step, index=index)

            if self.__record.get('status', step=step, index=index) == NodeStatus.ERROR:
                info["proc"] = None
                continue

            # If there are no dependencies left, launch this node and
            # remove from nodes_to_run.
            if ready and self.__allow_start(node):
                self.__logger.debug(f'Launching {info["name"]}')

                TaskScheduler.__callbacks['pre_node'](self.__chip, step, index)

                self.__record.set('status', NodeStatus.RUNNING, step=step, index=index)
                self.__startTimes[node] = time.time()
                changed = True

                # Start the process
                info["running"] = True
                info["proc"].start()

        return changed

    def check(self):
        exit_steps = set([step for step, _ in self.__runtime_flow.get_exit_nodes()])
        completed_steps = set([step for step, _ in
                               self.__runtime_flow.get_completed_nodes(record=self.__record)])

        unreached = set(exit_steps).difference(completed_steps)

        if unreached:
            raise RuntimeError(
                f'These final steps could not be reached: {", ".join(sorted(unreached))}')
