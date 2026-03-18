import os.path

from siliconcompiler import Task


class Convert(Task):
    '''
    Convert VCD waveform file to FST waveform file
    '''
    def tool(self):
        return "vcd2fst"

    def task(self):
        return "convert"

    def setup(self):
        super().setup()

        self.set_exe("vcd2fst")

        if f"{self.design_topmodule}.vcd" in self.get_files_from_input_nodes():
            self.add_input_file(ext="vcd")
        else:
            for lib, fileset in self.project.get_filesets():
                if lib.has_file(fileset=fileset, filetype="vcd"):
                    self.add_required_key(lib, "fileset", fileset, "file", "vcd")
                    break
        self.add_output_file(ext="fst")

    def runtime_options(self):
        options = super().runtime_options()

        infile = f"inputs/{self.design_topmodule}.vcd"
        if not os.path.exists(infile):
            for lib, fileset in self.project.get_filesets():
                files = lib.get_file(fileset=fileset, filetype="vcd")
                if files:
                    infile = files[0]
                    break
        options.extend([f"--vcdname={infile}"])
        options.extend([f"--fstname=outputs/{self.design_topmodule}.fst"])

        return options
