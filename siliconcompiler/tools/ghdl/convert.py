from siliconcompiler import Task


class ConvertTask(Task):
    '''
    Imports VHDL and converts it to verilog
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("use_fsynopsys", "bool", "add the -fsynopsys flag", defvalue=False)
        self.add_parameter("use_latches", "bool", "add the --latches flag", defvalue=False)

    def set_usefsynopsys(self, value: bool):
        self.set("var", "use_fsynopsys", value)

    def set_uselatches(self, value: bool):
        self.set("var", "use_latches", value)

    def tool(self):
        return "ghdl"

    def task(self):
        return "convert"

    def parse_version(self, stdout):
        # first line: GHDL 2.0.0-dev (1.0.0.r827.ge49cb7b9) [Dunoon edition]

        # '*-dev' is interpreted by packaging.version as a "developmental release",
        # which has the correct semantics. e.g. Version('2.0.0') > Version('2.0.0-dev')
        return stdout.split()[1]

    def setup(self):
        super().setup()

        self.set_exe("ghdl", vswitch="--version")
        self.add_version(">=4.0.0-dev")

        self.set_threads(1)

        self.set_logdestination("stdout", "output", "v")

        self.add_output_file(ext="v")

        self.add_required_key("option", "design")
        self.add_required_key("option", "fileset")
        if self.project.get("option", "alias"):
            self.add_required_key("option", "alias")

        # Mark required
        for lib, fileset in self.project.get_filesets():
            if lib.get("fileset", fileset, "define"):
                self.add_required_key(lib, "fileset", fileset, "define")
            if lib.has_file(fileset=fileset, filetype="vhdl"):
                self.add_required_key(lib, "fileset", fileset, "file", "vhdl")

        self.add_required_key("var", "use_fsynopsys")
        self.add_required_key("var", "use_latches")

    def runtime_options(self):
        options = super().runtime_options()

        # Synthesize inputs and output Verilog netlist
        options.append('--synth')
        options.append('--std=08')
        options.append('--out=verilog')
        options.append('--no-formal')

        if self.get("var", "use_fsynopsys"):
            options.append('-fsynopsys')
        if self.get("var", "use_latches"):
            options.append('--latches')

        filesets = self.project.get_filesets()
        defines = []
        for lib, fileset in filesets:
            defines.extend(lib.get("fileset", fileset, "define"))

        # Add defines
        for define in defines:
            options.append(f'-g{define}')

        # Add sources
        for lib, fileset in filesets:
            for value in lib.get_file(fileset=fileset, filetype="vhdl"):
                options.append(value)

        # Set top module
        options.append('-e')

        options.append(self.design_topmodule)

        return options
