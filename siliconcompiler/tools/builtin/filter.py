import fnmatch
import shutil

from typing import Optional, List, Union

from siliconcompiler import Task
from siliconcompiler import utils


class FilterTask(Task):
    '''
    A task for filtering files based on specified glob patterns.
    
    This task determines which files to "keep" from a given set of inputs,
    passing only those that match the criteria to the outputs.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("keep", "[str]", "Glob of files to keep")

    def add_filter_keep(self, keep: Union[List[str], str],
                        step: Optional[str] = None, index: Optional[str] = None,
                        clobber: bool = False) -> None:
        '''
        Adds one or more glob patterns for files to keep.

        Args:
            keep (Union[List[str], str]): A single glob pattern or a list of
                glob patterns to identify which files should be kept.
            step (Optional[str], optional): The specific workflow step to
                apply this filter to. Defaults to None.
            index (Optional[str], optional): The specific index within the step
                to apply this filter to. Defaults to None.
            clobber (bool, optional): If True, existing 'keep' patterns are
                overwritten with the new value(s). If False, the new patterns
                are appended to the existing list. Defaults to False.
        '''
        if clobber:
            self.set("var", "keep", keep, step=step, index=index)
        else:
            self.add("var", "keep", keep, step=step, index=index)

    def tool(self):
        return "builtin"

    def task(self):
        return "filter"

    def setup(self):
        super().setup()

        if self.get("var", "keep"):
            self.add_required_key("var", "keep")

        files = sorted(list(self.get_files_from_input_nodes().keys()))
        if not files:
            raise ValueError("task receives no files")

        filters: List[str] = self.get("var", "keep")
        if not filters:
            filters = ["*"]

        keep_files = []
        for keep in filters:
            keep_files.extend(fnmatch.filter(files, keep))

        if not keep_files:
            self.logger.warning(f"Filters ({', '.join(filters)}) removed all incoming files")
        else:
            self.add_input_file(keep_files)
            self.add_output_file(keep_files)

    def run(self):
        self.logger.info(f"Running builtin task '{self.task()}'")

        shutil.copytree('inputs', 'outputs', dirs_exist_ok=True,
                        copy_function=utils.link_symlink_copy)

        return 0

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
