from typing import Optional, Union
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

        self.add_parameter("trace", "bool",
                           'Enable waveform tracing. When enabled, a VCD dump module is '
                           'auto-generated and compiled with the design to capture all signals.',
                           defvalue=False)

    def set_icarus_veriloggeneration(self, gen: str,
                                     step: Optional[str] = None,
                                     index: Optional[str] = None):
        """
        Sets the Verilog language generation for Icarus.

        Args:
            gen (str): The Verilog generation to use.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "verilog_generation", gen, step=step, index=index)

    def set_trace_enabled(self, enabled: bool = True,
                          step: Optional[str] = None,
                          index: Optional[Union[str, int]] = None):
        """
        Enables or disables waveform tracing.

        When enabled, a VCD dump module is auto-generated and compiled with
        the design. The waveform file will be written to reports/<topmodule>.vcd.

        Args:
            enabled (bool): Whether to enable tracing. Defaults to True.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "trace", enabled, step=step, index=index)

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

    def pre_process(self):
        super().pre_process()

        # Generate VCD dump module if tracing is enabled
        if self.get("var", "trace"):
            self._generate_trace_module()

    def _generate_trace_module(self):
        trace_file = f"reports/{self.design_topmodule}.vcd"
        dump_module = f"""// Auto-generated waveform dump module
module sc_trace_dump();
initial begin
    $dumpfile("{trace_file}");
    $dumpvars(0, {self.design_topmodule});
end
endmodule
"""
        with open("sc_trace_dump.v", "w") as f:
            f.write(dump_module)

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

        # Add trace dump module if tracing is enabled
        if self.get("var", "trace"):
            options.append("sc_trace_dump.v")
            options.extend(["-s", "sc_trace_dump"])

        return options
