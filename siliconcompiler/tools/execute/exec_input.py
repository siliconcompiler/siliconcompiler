import glob
import stat

import os.path

from siliconcompiler import TaskSchema


class ExecInputTask(TaskSchema):
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

        files = self.get_files_from_input_nodes().keys()
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
            raise FileNotFoundError(f'{self.step}/{self.index} did not receive an executable file')

        os.chmod(exec, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        return exec
