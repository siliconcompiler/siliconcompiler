import re
import os.path

from siliconcompiler import ShowTask


class ShowTask(ShowTask):
    '''
    Show a VCD or FST file.
    '''
    def tool(self):
        return "gtkwave"

    def get_supported_task_extentions(self):
        return ["vcd", "fst"]

    def parse_version(self, stdout):
        # First line: GTKWave Analyzer v3.3.116 (w)1999-2023 BSI
        #
        # 🔴 Matched rather than counted. This took the third WORD, and
        # gtkwave answers `--version` with "Could not initialize GTK!  Is
        # DISPLAY env var/xhost set?" when it has no display -- so the third
        # word was "initialize", and that was reported as the version. It then
        # failed the version check with a message about "initialize" not being
        # a version, which says nothing about the missing display.
        found = re.search(r"GTKWave\s+Analyzer\s+v?(\S+)", stdout)
        if not found:
            raise ValueError(
                "gtkwave did not report a version. It needs a display to "
                "answer --version at all, so this is most likely DISPLAY "
                f"being unset. It said: {stdout.strip().splitlines()[0]!r}"
                if stdout.strip() else
                "gtkwave printed nothing in answer to --version")
        return found.group(1)

    def normalize_version(self, version):
        if version[0] == 'v':
            return version[1:]
        return version

    def setup(self):
        super().setup()

        self.set_exe("gtkwave", vswitch="--version", format="tcl")
        self.add_version(">=3.3.116")

        self.set_threads()

        self.set_dataroot("gtkwave", __file__)
        with self.active_dataroot("gtkwave"):
            self.set_refdir("scripts")
        self.set_script("sc_show.tcl")

        if f"{self.design_topmodule}.vcd" in self.get_files_from_input_nodes():
            self.add_input_file(ext="vcd")
        elif f"{self.design_topmodule}.fst" in self.get_files_from_input_nodes():
            self.add_input_file(ext="fst")
        else:
            self.add_required_key("var", "showfilepath")

    def runtime_options(self):
        options = []

        options.append(f'--cpu={self.get_threads()}')
        options.append(f'--script={self.find_files("script")[0]}')

        if os.path.exists(f'inputs/{self.design_topmodule}.vcd'):
            dump = f'inputs/{self.design_topmodule}.vcd'
        elif os.path.exists(f'inputs/{self.design_topmodule}.fst'):
            dump = f'inputs/{self.design_topmodule}.fst'
        else:
            dump = self.find_files('var', 'showfilepath')
        options.append(f'--dump={dump}')

        return options
