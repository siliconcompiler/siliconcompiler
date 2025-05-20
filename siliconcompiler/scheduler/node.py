import multiprocessing
import shutil

import os.path

from siliconcompiler import utils
from siliconcompiler import Schema


class SchedulerNode:
    def __init__(self, step, index, chip):
        self.__step = step
        self.__index = index
        self.__chip = chip

        self.__design = self.__chip.design

        self.__job = chip.get('option', 'jobname')

        flow = chip.get('option', 'flow')
        tool = chip.get('flowgraph', flow, self.__step, self.__index, 'tool')
        task = chip.get('flowgraph', flow, self.__step, self.__index, 'task')

        self.__task = chip.schema.get("tool", tool, "task", task, field="schema")
        self.__logger = chip.logger

        self.__workdir = chip.getworkdir(jobname=self.__job, step=self.__step, index=self.__index)
        self.__manifests = {
            "input": os.path.join(self.__workdir, "inputs", f"{self.__design}.pkg.json"),
            "output": os.path.join(self.__workdir, "outputs", f"{self.__design}.pkg.json")
        }
        self.__replay = os.path.join(self.__workdir, "replay.sh")

        self.__state = None

        self.__parent_pipe, self.__child_pipe = multiprocessing.Pipe()
        self.set_queue(None)

    def set_queue(self, queue):
        self.__proc_queue = queue

    def reset(self):
        pass

    def clean(self):
        if os.path.isdir(self.__workdir):
            shutil.rmtree(self.__workdir)

    def setup(self):
        pass

    def requires_run(self):
        return True

    def copy_from(self, task):
        if not os.path.isdir(task.__workdir):
            return

        self.__logger.info(f"Importing {self.__step}{self.__index} from {task.__job}: {task.__workddir}")

        shutil.copytree(task.__workddir, self.__workddir,
                        dirs_exist_ok=True,
                        copy_function=utils.link_copy)

        # Rewrite replay
        if os.path.exists(self.__replay):
            # delete file as it might be a hard link
            os.remove(self.__replay)

            self.__chip.set('arg', 'step', self.__step)
            self.__chip.set('arg', 'index', self.__index)
            self.__task.set_runtime(self.__chip)

            self.__task.generate_replay_script(self.__replay, self.__workdir)

            self.__chip.unset('arg', 'step')
            self.__chip.unset('arg', 'index')
            self.__task.set_runtime(None)

        # Rewrite manifests
        for manifest in self.__manifests.values():
            if os.path.exists(manifest):
                schema = Schema.from_manifest(filepath=manifest)
                # delete file as it might be a hard link
                os.remove(manifest)
                schema.set('option', 'jobname', self.__job)
                schema.write_manifest(manifest)

    def run(self):
        pass
