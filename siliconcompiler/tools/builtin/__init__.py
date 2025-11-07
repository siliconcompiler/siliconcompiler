'''
Builtin tools for SiliconCompiler
'''
import shutil

from siliconcompiler import NodeStatus

from siliconcompiler import Task
from siliconcompiler import utils


class BuiltinTask(Task):
    def __init__(self):
        super().__init__()

    def tool(self):
        return "builtin"

    def setup(self):
        super().setup()

        self._set_io_files()

        self.set_threads(1)

    def _set_io_files(self):
        files = sorted(list(self.get_files_from_input_nodes().keys()))
        self.add_input_file(files)
        self.add_output_file(files)

    def select_input_nodes(self):
        self.logger.info(f"Running builtin task '{self.task()}'")

        return super().select_input_nodes()

    def run(self):
        # Do nothing
        return 0

    def post_process(self):
        super().post_process()
        shutil.copytree('inputs', 'outputs', dirs_exist_ok=True,
                        copy_function=utils.link_symlink_copy)

    @classmethod
    def make_docs(cls):
        from siliconcompiler import Flowgraph, Design, Project
        from siliconcompiler.scheduler import SchedulerNode
        from siliconcompiler.tools.builtin.nop import NOPTask
        design = Design("<design>")
        with design.active_fileset("docs"):
            design.set_topmodule("top")
        proj = Project(design)
        proj.add_fileset("docs")
        flow = Flowgraph("docsflow")
        flow.node("<in>", NOPTask())
        flow.node("<step>", cls(), index="<index>")
        flow.edge("<in>", "<step>", head_index="<index>")
        flow.set("<step>", "<index>", "args", "errors==0")
        proj.set_flow(flow)

        NOPTask.find_task(proj).add_output_file("<top>.v", step="<in>", index="0")
        node = SchedulerNode(proj, "<step>", "<index>")
        node.setup()
        return node.task


class MinMaxBuiltinTask(BuiltinTask):
    def task(self):
        return self._mode()

    def _mode(self):
        raise NotImplementedError("must be implemented by child class")

    def select_input_nodes(self):
        op = self._mode()

        if op not in ('minimum', 'maximum'):
            raise ValueError('Invalid op')

        nodelist = list(super().select_input_nodes())

        # Keeping track of the steps/indexes that have goals met
        failed = {}
        for step, index in nodelist:
            if step not in failed:
                failed[step] = {}
            failed[step][index] = False

            if self.schema_record.get('status', step=step, index=index) == NodeStatus.ERROR:
                failed[step][index] = True
            else:
                for metric in self.schema_metric.getkeys():
                    if self.schema_flow.valid(step, index, 'goal', metric):
                        goal = self.schema_flow.get(step, index, 'goal', metric)
                        real = self.schema_metric.get(metric, step=step, index=index)
                        if real is None:
                            raise ValueError(
                                f'Metric {metric} has goal for {step}/{index} '
                                'but it has not been set.')
                        if abs(real) > goal:
                            self.logger.warning(f"Step {step}/{index} failed "
                                                f"because it didn't meet goals for '{metric}' "
                                                "metric.")
                            failed[step][index] = True

        # Calculate max/min values for each metric
        max_val = {}
        min_val = {}
        for metric in self.schema_metric.getkeys():
            max_val[metric] = 0
            min_val[metric] = float("inf")
            for step, index in nodelist:
                if not failed[step][index]:
                    real = self.schema_metric.get(metric, step=step, index=index)
                    if real is None:
                        continue
                    max_val[metric] = max(max_val[metric], real)
                    min_val[metric] = min(min_val[metric], real)

        # Select the minimum index
        best_score = float('inf') if op == 'minimum' else float('-inf')
        winner = None
        for step, index in nodelist:
            if failed[step][index]:
                continue

            score = 0.0
            for metric in self.schema_flow.getkeys(step, index, 'weight'):
                weight = self.schema_flow.get(step, index, 'weight', metric)
                if not weight:
                    # skip if weight is 0 or None
                    continue

                real = self.schema_metric.get(metric, step=step, index=index)
                if real is None:
                    raise ValueError(
                        f'Metric {metric} has weight for {step}/{index} '
                        'but it has not been set.',)

                if not (max_val[metric] - min_val[metric]) == 0:
                    scaled = (real - min_val[metric]) / (max_val[metric] - min_val[metric])
                else:
                    scaled = max_val[metric]
                score = score + scaled * weight

            if ((op == 'minimum' and score < best_score) or
                    (op == 'maximum' and score > best_score)):
                best_score = score
                winner = (step, index)

        if winner:
            self.logger.info(f"Selected '{winner[0]}/{winner[1]}' with score {best_score:.3f}")
            return [winner]
        return []
