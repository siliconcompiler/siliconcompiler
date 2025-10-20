from siliconcompiler import Task


class CompileTask(Task):
    '''
    Compile the input verilog into a vvp file that can be simulated.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("verilog_generation", "<1995,2001,2001-noconfig,2005,2005-sv,2009,2012>",
                           'Select Verilog language generation for Icarus to use. Legal values are '
                           '"1995", "2001", "2001-noconfig", "2005", "2005-sv", "2009", or "2012". '
                           'See the corresponding "-g" flags in the Icarus manual for more "'
                           '"information.')

    def tool(self):
        return "icarus"

    def task(self):
        return "compile"

    def parse_version(self, stdout):
        # First line: Icarus Verilog version 10.1 (stable) ()
        return stdout.split()[3]

    def setup(self):
        super().setup()

        self.set_exe("iverilog", vswitch="-V")
        self.add_version(">=10.3")

        self.set_threads()

        self.add_output_file(ext="vvp")

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

        if self.get("var", "verilog_generation"):
            self.add_required_key("var", "verilog_generation")

    def runtime_options(self):
        options = super().runtime_options()

        options.extend(["-o", f"outputs/{self.design_topmodule}.vvp"])
        options.extend(["-s", self.design_topmodule])

        verilog_gen = self.get("var", "verilog_generation")
        if verilog_gen:
            options.append(f'-g{verilog_gen}')

        filesets = self.project.get_filesets()
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

        ###############################
        # Parameters (top module only)
        ###############################
        # Set up user-provided parameters to ensure we elaborate the correct modules
        for param, value in params:
            options.append(f"-P{self.design_topmodule}.{param}={value}")

        #####################
        # Include paths
        #####################
        for idir in idirs:
            options.append('-I' + idir)

        #######################
        # Variable Definitions
        #######################
        for define in defines:
            options.append('-D' + define)

        # add siliconcompiler specific defines
        options.append("-DSILICONCOMPILER_TRACE_DIR=\"reports\"")
        options.append(f"-DSILICONCOMPILER_TRACE_FILE=\"reports/{self.design_topmodule}.vcd\"")

        #######################
        # Command files
        #######################
        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="commandfile"):
                options.extend(['-f', value])

        #######################
        # Sources
        #######################
        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="systemverilog"):
                options.append(value)
        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="verilog"):
                options.append(value)

        return options
