'''
Verilator is a free and open-source software tool which converts Verilog (a
hardware description language) to a cycle-accurate behavioral model in C++
or SystemC.

For all tasks, this driver runs Verilator using the ``-sv`` switch to enable
parsing a subset of SystemVerilog features.

Documentation: https://verilator.org/guide/latest

Sources: https://github.com/verilator/verilator

Installation: https://verilator.org/guide/latest/install.html
'''

import os.path

from siliconcompiler import Task


class VerilatorTask(Task):
    def __init__(self):
        super().__init__()

        self.add_parameter("config", "[file]", "Verilator configuration file")
        self.add_parameter("enable_assert", "bool",
                           "true/false, when true assertions are enabled in Verilator.")

    def tool(self):
        return "verilator"

    def setup(self):
        super().setup()

        self.set_exe("verilator", vswitch="--version")
        self.add_version(">=4.034")

        self.add_regex("warnings", r"^\%Warning")
        self.add_regex("errors", r"^\%Error")

        self.add_required_key("var", "enable_assert")
        if self.get("var", "config"):
            self.add_required_key("var", "config")

        self.add_required_key("option", "design")
        self.add_required_key("option", "fileset")
        if self.project.get("option", "alias"):
            self.add_required_key("option", "alias")

        add_inputs = False
        if f"{self.design_topmodule}.sv" in self.get_files_from_input_nodes():
            self.add_input_file(ext="sv")
        elif f"{self.design_topmodule}.v" in self.get_files_from_input_nodes():
            self.add_input_file(ext="v")
        else:
            add_inputs = True

        # Mark required
        for lib, fileset in self.project.get_filesets():
            if lib.has_idir(fileset):
                self.add_required_key(lib, "fileset", fileset, "idir")
            if lib.get("fileset", fileset, "define"):
                self.add_required_key(lib, "fileset", fileset, "define")
            if lib.has_file(fileset=fileset, filetype="commandfile"):
                self.add_required_key(lib, "fileset", fileset, "file", "commandfile")
            if add_inputs:
                if lib.has_file(fileset=fileset, filetype="systemverilog"):
                    self.add_required_key(lib, "fileset", fileset, "file", "systemverilog")
                if lib.has_file(fileset=fileset, filetype="verilog"):
                    self.add_required_key(lib, "fileset", fileset, "file", "verilog")

        fileset = self.project.get("option", "fileset")[0]
        design = self.project.design
        for param in design.getkeys("fileset", fileset, "param"):
            self.add_required_key(design, "fileset", fileset, "param", param)

    def parse_version(self, stdout):
        # Verilator 4.104 2020-11-14 rev v4.104
        return stdout.split()[1]

    def runtime_options(self):
        filesets = self.project.get_filesets()

        options = super().runtime_options()

        options.append("-sv")
        options.extend(['--top-module', self.design_topmodule])

        if self.get("var", "enable_assert"):
            options.append("--assert")

        # Converting user setting to verilator specific filter
        for warning in self.get('warningoff'):
            options.append(f'-Wno-{warning}')

        for cmdfile in self.find_files("var", "config"):
            options.append(cmdfile)

        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="verilatorctrlfile"):
                options.append(value)

        idirs = []
        defines = []
        params = []
        for lib, fileset in filesets:
            idirs.extend(lib.get_idir(fileset))
            defines.extend(lib.get("fileset", fileset, "define"))
        fileset = self.project.get("option", "fileset")[0]

        design = self.project.design
        for param in design.getkeys("fileset", fileset, "param"):
            params.append((param, design.get("fileset", fileset, "param", param)))

        fileset = self.project.get("option", "fileset")[0]
        design = self.project.design
        for param in design.getkeys("fileset", fileset, "param"):
            value = design.get("fileset", fileset, "param", param)
            value = value.replace('"', '\\"')
            options.append(f'-G{param}={value}')

        if os.path.isfile(f'inputs/{self.design_topmodule}.sv'):
            options.append(f'inputs/{self.design_topmodule}.sv')
        elif os.path.isfile(f'inputs/{self.design_topmodule}.v'):
            options.append(f'inputs/{self.design_topmodule}.v')
        else:
            for value in idirs:
                options.append(f'-I{value}')
            for value in defines:
                if value == "VERILATOR":
                    # Verilator auto defines this and will error if it is defined twice.
                    continue
                options.append(f'-D{value}')

            #######################
            # Sources
            #######################
            for lib, fileset in filesets:
                for value in lib.get_file(fileset=fileset, filetype="systemverilog"):
                    options.append(value)
            for lib, fileset in filesets:
                for value in lib.get_file(fileset=fileset, filetype="verilog"):
                    options.append(value)

        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="commandfile"):
                options.extend(['-f', value])

        return options
