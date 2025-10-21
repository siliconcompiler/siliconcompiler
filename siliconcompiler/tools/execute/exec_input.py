import glob
import stat

import os.path

from siliconcompiler import Task
from siliconcompiler.tool import TaskExecutableNotReceived


class ExecInputTask(Task):
    '''
    Execute the output of the previous step directly.
    This only works if the task receives a single file.
    '''
    def __init__(self):
        super().__init__()

    def tool(self):
        return "execute"

    def task(self):
        return "exec_input"

    def setup(self):
        super().setup()

        files = list(self.get_files_from_input_nodes().keys())
        if len(files) == 0:
            raise ValueError("must receive one input file")
        elif len(files) > 1:
            raise ValueError("execute only supports one input file")

        self.add_input_file(files[0])

    def get_exe(self):
        exec = None
        for fin in glob.glob('inputs/*'):
            if fin.endswith('.pkg.json'):
                continue
            exec = os.path.abspath(fin)
            break

        if not exec:
            raise TaskExecutableNotReceived(f'{self.step}/{self.index} did not receive an '
                                            'executable file')

        os.chmod(exec, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        return exec

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

        NOPTask.find_task(proj).add_output_file("<top>.exe", step="<in>", index="0")
        node = SchedulerNode(proj, "<step>", "<index>")
        node.setup()
        return node.task
