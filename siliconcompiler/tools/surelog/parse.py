import re
import sys

import os.path

from siliconcompiler import sc_open
from siliconcompiler import utils

from siliconcompiler import Task


class ElaborateTask(Task):
    def __init__(self):
        super().__init__()

        self.add_parameter("enable_lowmem", "bool",
                           "true/false, when true instructs Surelog to minimize its maximum "
                           "memory usage.")
        self.add_parameter("disable_write_cache", "bool",
                           "true/false, when true instructs Surelog to not write to its cache.")
        self.add_parameter("disable_info", "bool",
                           "true/false, when true instructs Surelog to not log infos.")
        self.add_parameter("disable_note", "bool",
                           "true/false, when true instructs Surelog to not log notes.")

    def tool(self):
        return "surelog"

    def task(self):
        return "elaborate"

    def parse_version(self, stdout):
        # Surelog --version output looks like:
        # VERSION: 1.13
        # BUILT  : Nov 10 2021

        # grab version # by splitting on whitespace
        return stdout.split()[1]

    def __outputfile(self):
        if self.get_fileset_file_keys("systemverilog"):
            return f"{self.design_topmodule}.sv"
        return f"{self.design_topmodule}.v"

    def setup(self):
        super().setup()

        is_docker = self.project.get('option', 'scheduler', 'name',
                                     step=self.step, index=self.index) == 'docker'
        if not is_docker:
            exe = 'surelog'
            if sys.platform.startswith("win32"):
                exe = f"{exe}.exe"
        else:
            exe = 'surelog'
        self.set_exe(exe, vswitch="--version")
        self.add_version(">=1.51")

        self.set_threads()

        self.add_regex("warnings", r'^\[WRN:')
        for warning in self.get("warningoff"):
            self.add_regex("warnings", f"-v {warning}")
        self.add_regex("errors", r'^\[(ERR|FTL|SNT):')

        self.add_required_key("var", "enable_lowmem")
        self.add_required_key("var", "disable_write_cache")
        self.add_required_key("var", "disable_info")
        self.add_required_key("var", "disable_note")

        self.add_required_key("option", "design")
        self.add_required_key("option", "fileset")
        if self.project.get("option", "alias"):
            self.add_required_key("option", "alias")

        # Mark required
        for lib, fileset in self.project.get_filesets():
            if lib.has_idir(fileset):
                self.add_required_key(lib, "fileset", fileset, "idir")
            if lib.get("fileset", fileset, "define"):
                self.add_required_key(lib, "fileset", fileset, "define")
            if lib.has_file(fileset=fileset, filetype="commandfile"):
                self.add_required_key(lib, "fileset", fileset, "file", "commandfile")
            if lib.has_file(fileset=fileset, filetype="systemverilog"):
                self.add_required_key(lib, "fileset", fileset, "file", "systemverilog")
            if lib.has_file(fileset=fileset, filetype="verilog"):
                self.add_required_key(lib, "fileset", fileset, "file", "verilog")

        fileset = self.project.get("option", "fileset")[0]
        design = self.project.design
        for param in design.getkeys("fileset", fileset, "param"):
            self.add_required_key(design, "fileset", fileset, "param", param)

        self.add_output_file(self.__outputfile())

    def runtime_options(self):
        options = super().runtime_options()
        options.append('-nocache')

        if self.get("var", "enable_lowmem"):
            options.append('-lowmem')

        if self.get("var", "disable_write_cache"):
            options.append('-nowritecache')

        if self.get("var", "disable_info"):
            options.append('-noinfo')

        if self.get("var", "disable_note"):
            options.append('-nonote')

        options.extend(["--threads", self.get_threads()])

        # -parse is slow but ensures the SV code is valid
        # we might want an option to control when to enable this
        # or replace surelog with a SV linter for the validate step
        options.append('-parse')
        # We don't use UHDM currently, so disable. For large designs, this file is
        # very big and takes a while to write out.
        options.append('-nouhdm')

        filesets = self.project.get_filesets()
        idirs = []
        defines = []
        for lib, fileset in filesets:
            idirs.extend(lib.get_idir(fileset))
            defines.extend(lib.get("fileset", fileset, "define"))

        params = []
        fileset = self.project.get("option", "fileset")[0]
        design = self.project.design
        for param in design.getkeys("fileset", fileset, "param"):
            params.append((param, design.get("fileset", fileset, "param", param)))

        options.append('+libext+.sv+.v')

        #####################
        # Include paths
        #####################
        for value in idirs:
            options.append('-I' + value)

        #######################
        # Variable Definitions
        #######################
        for value in defines:
            options.append('-D' + value)

        #######################
        # Command files
        #######################
        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="commandfile"):
                options.extend(['-f', + value])

        #######################
        # Sources
        #######################
        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="systemverilog"):
                options.append(value)
        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="verilog"):
                options.append(value)

        #######################
        # Top Module
        #######################
        options.extend(['-top', self.design_topmodule])

        ###############################
        # Parameters (top module only)
        ###############################
        # Set up user-provided parameters to ensure we elaborate the correct modules
        for param, value in params:
            options.append(f'-P{param}={value}')

        return options

    def post_process(self):
        super().post_process()

        filemap = []
        with sc_open('slpp_all/file_map.lst') as filelist:
            for mapping in filelist:
                filemap.append(mapping)

        def lookup_sources(file):
            for fmap in filemap:
                if fmap.startswith(file):
                    return fmap[len(file):].strip()
            return "unknown"

        # https://github.com/chipsalliance/Surelog/issues/3776#issuecomment-1652465581
        surelog_escape = re.compile(r"#~@([a-zA-Z_0-9.\$/\:\[\] ]*)#~@")

        # Look in slpp_all/file_elab.lst for list of Verilog files included in
        # design, read these and concatenate them into one pickled output file.
        output_template = utils.get_file_template(
            'output.v',
            root=os.path.join(os.path.dirname(__file__), 'templates'))

        with sc_open('slpp_all/file_elab.lst') as filelist, \
                open(f'outputs/{self.__outputfile()}', 'w') as outfile:
            for path in filelist.read().split('\n'):
                path = path.strip('"')
                if not path:
                    # skip empty lines
                    continue
                with sc_open(path) as infile:
                    source_files = lookup_sources(path)
                    unescaped_data = surelog_escape.sub(r"\\\1 ", infile.read())

                    outfile.write(output_template.render(
                        source_file=source_files,
                        content=unescaped_data
                    ))

                    outfile.write('\n')
