import shutil

from siliconcompiler import TaskSchema
from siliconcompiler import utils


class BuiltinTask(TaskSchema):
    def __init__(self):
        super().__init__()

    def tool(self):
        return "builtin"

    def _set_io_files(self):
        pass

    def select_input_nodes(self):
        self.logger.info(f"Running builtin task '{self.task()}'")

        return super().select_input_nodes()
        # flow = chip.get('option', 'flow')

        # flow_schema = chip.get("flowgraph", flow, field="schema")
        # runtime = RuntimeFlowgraph(
        #     flow_schema,
        #     from_steps=set([step for step, _ in flow_schema.get_entry_nodes()]),
        #     prune_nodes=chip.get('option', 'prune'))

        # return runtime.get_node_inputs(step, index, record=chip.get("record", field="schema"))

    def run(self):
        # Do nothing
        return 0

    def post_process(self):
        super().post_process()
        shutil.copytree('inputs', 'outputs', dirs_exist_ok=True,
                        copy_function=utils.link_symlink_copy)
