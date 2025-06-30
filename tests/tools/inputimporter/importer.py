import shutil

import os.path

from siliconcompiler import TaskSchema


class ImporterTask(TaskSchema):
    '''
    Import (copy) files into the output folder.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("input_files", "[file]", "input files to copy")

    def tool(self):
        return "testing"

    def task(self):
        return "importer"

    def setup(self):
        super().setup()

        self.add_required_tool_key("var", "input_files")

        for file in self.get("var", "input_files"):
            self.add_output_file(os.path.basename(file))

    def run(self):
        for file in self.find_files("var", "input_files"):
            shutil.copy2(file, "outputs/")
        return 0
