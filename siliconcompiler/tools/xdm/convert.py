import shutil

import os.path

from siliconcompiler import Task


class ConvertTask(Task):
    def __init__(self):
        super().__init__()

        self.add_parameter("rename", "bool",
                           "true/false: indicate whether to rename the output file to match "
                           "the naming scheme for siliconcompiler",
                           defvalue=True)

    def tool(self):
        return "xdm"

    def task(self):
        return "convert"

    def parse_version(self, stdout):
        line = stdout.splitlines()[5]
        return line.split()[1]

    def setup(self):
        super().setup()

        self.set_exe("xdm_bdl", vswitch="-h")
        self.add_version(">=v2.7.0")

        # Mark required
        self.add_required_key("var", "rename")

        if f"{self.design_topmodule}.cir" in self.get_files_from_input_nodes():
            self.add_input_file(ext="cir")
        elif f"{self.design_topmodule}.spice" in self.get_files_from_input_nodes():
            self.add_input_file(ext="spice")
        else:
            for lib, fileset in self.project.get_filesets():
                if lib.has_file(fileset=fileset, filetype="spice"):
                    self.add_required_key(lib, "fileset", fileset, "file", "spice")

    def __input_file(self):
        if os.path.exists(f"inputs/{self.design_topmodule}.cir"):
            return f"inputs/{self.design_topmodule}.cir"
        elif os.path.exists(f"inputs/{self.design_topmodule}.spice"):
            return f"inputs/{self.design_topmodule}.spice"
        else:
            for lib, fileset in self.project.get_filesets():
                files = lib.get_file(fileset=fileset, filetype="spice")
                if files:
                    return files[0]

    def runtime_options(self):
        options = super().runtime_options()
        options.append("--auto")
        options.extend(['--source_file_format', 'hspice'])
        options.extend(['--dir_out', f'outputs/{self.design_topmodule}.xyce'])
        options.append(self.__input_file())

    def post_process(self):
        super().post_process()

        if not self.get("var", "rename"):
            return

        basename = os.path.basename(self.__input_file())
        outdir = f'outputs/{self.design_topmodule}.xyce'
        outputfile_base = f'{self.design_topmodule}.cir'

        if basename != outputfile_base:
            shutil.move(os.path.join(outdir, basename), os.path.join(outdir, outputfile_base))
