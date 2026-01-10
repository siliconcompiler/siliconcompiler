import shlex
from typing import Optional, List, Union

from siliconcompiler.tools.verilator import VerilatorTask


class CompileTask(VerilatorTask):
    '''
    Compiles Verilog and C/C++ sources into an executable. In addition to the
    standard RTL inputs, this task reads C/C++ sources.
    Outputs an executable in ``outputs/<design>.vexe``.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("mode", "<cc,systemc>", "defines compilation mode for Verilator",
                           defvalue="cc")
        self.add_parameter("trace", "bool", "if true, enables trace generation")
        self.add_parameter("trace_type", "<vcd,fst>",
                           "specifies type of wave file to create when [trace] is set",
                           defvalue="vcd")

        # TODO Move to design object
        self.add_parameter("cincludes", "[dir]",
                           "include directories to provide to the C++ compiler invoked "
                           "by Verilator")
        self.add_parameter("cflags", "[str]",
                           "flags to provide to the C++ compiler invoked by Verilator")
        self.add_parameter("ldflags", "[str]",
                           "flags to provide to the linker invoked by Verilator")

        self.add_parameter("pins_bv", "int",
                           "controls datatypes used to represent SystemC inputs/outputs. "
                           "See --pins-bv in Verilator docs for more info")

        self.add_parameter("initialize_random", "bool",
                           "true/false, when true registers will reset with a random value")

    def set_verilator_mode(self, mode: str,
                           step: Optional[str] = None,
                           index: Optional[str] = None):
        """
        Sets the compilation mode for Verilator.

        Args:
            mode (str): The compilation mode.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "mode", mode, step=step, index=index)

    def set_verilator_trace(self, enable: bool,
                            step: Optional[str] = None,
                            index: Optional[str] = None):
        """
        Enables or disables trace generation.

        Args:
            enable (bool): Whether to enable trace generation.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "trace", enable, step=step, index=index)

    def set_verilator_tracetype(self, trace_type: str,
                                step: Optional[str] = None,
                                index: Optional[str] = None):
        """
        Sets the type of wave file to create when trace is enabled.

        Args:
            trace_type (str): The trace type.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "trace_type", trace_type, step=step, index=index)

    def add_verilator_cincludes(self, include: Union[str, List[str]],
                                step: Optional[str] = None,
                                index: Optional[str] = None,
                                clobber: bool = False):
        """
        Adds include directories for the C++ compiler.

        Args:
            include (Union[str, List[str]]): The include directory/directories to add.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
            clobber (bool, optional): If True, overwrites the existing list. Defaults to False.
        """
        if clobber:
            self.set("var", "cincludes", include, step=step, index=index)
        else:
            self.add("var", "cincludes", include, step=step, index=index)

    def add_verilator_cflags(self, flag: Union[str, List[str]],
                             step: Optional[str] = None,
                             index: Optional[str] = None,
                             clobber: bool = False):
        """
        Adds flags for the C++ compiler.

        Args:
            flag (Union[str, List[str]]): The flag(s) to add.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
            clobber (bool, optional): If True, overwrites the existing list. Defaults to False.
        """
        if clobber:
            self.set("var", "cflags", flag, step=step, index=index)
        else:
            self.add("var", "cflags", flag, step=step, index=index)

    def add_verilator_ldflags(self, flag: Union[str, List[str]],
                              step: Optional[str] = None,
                              index: Optional[str] = None,
                              clobber: bool = False):
        """
        Adds flags for the linker.

        Args:
            flag (Union[str, List[str]]): The flag(s) to add.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
            clobber (bool, optional): If True, overwrites the existing list. Defaults to False.
        """
        if clobber:
            self.set("var", "ldflags", flag, step=step, index=index)
        else:
            self.add("var", "ldflags", flag, step=step, index=index)

    def set_verilator_pinsbv(self, width: int,
                             step: Optional[str] = None,
                             index: Optional[str] = None):
        """
        Sets the datatype width for SystemC inputs/outputs.

        Args:
            width (int): The bit width.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "pins_bv", width, step=step, index=index)

    def set_verilator_initializerandom(self, enable: bool,
                                       step: Optional[str] = None,
                                       index: Optional[str] = None):
        """
        Enables or disables random initialization of registers.

        Args:
            enable (bool): Whether to enable random initialization.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "initialize_random", enable, step=step, index=index)

    def task(self):
        return "compile"

    def setup(self):
        super().setup()
        self.set_threads()

        self.add_output_file(ext="vexe")

        # Mark required
        self.add_required_key("var", "mode")
        self.add_required_key("var", "trace")
        self.add_required_key("var", "trace_type")
        self.add_required_key("var", "initialize_random")

        added_key = False
        for lib, fileset in self.project.get_filesets():
            if lib.has_file(fileset=fileset, filetype="c"):
                self.add_required_key(lib, "fileset", fileset, "file", "c")
                added_key = True
        if not added_key:
            self.add_required_key(self.project.design, "fileset",
                                  self.project.get("option", "fileset")[0], "file", "c")

        if self.get("var", "cincludes"):
            self.add_required_key("var", "cincludes")
        if self.get("var", "cflags"):
            self.add_required_key("var", "cflags")
        if self.get("var", "ldflags"):
            self.add_required_key("var", "ldflags")

        if self.get("var", "pins_bv") is not None:
            self.add_required_key("var", "pins_bv")

    def runtime_options(self):
        options = super().runtime_options()

        if self.get("var", "initialize_random"):
            options.extend(['--x-assign', 'unique'])

        options.extend(['--exe', '--build'])

        options.extend(['-j', self.get_threads()])

        mode = self.get("var", "mode")
        if mode == "cc":
            options.append('--cc')
        elif mode == 'systemc':
            options.append('--sc')
        else:
            raise ValueError("mode invalid")

        pins_bv = self.get('var', 'pins_bv')
        if pins_bv is not None:
            options.extend(['--pins-bv', pins_bv])

        options.extend(['-o', f'../outputs/{self.design_topmodule}.vexe'])

        c_flags = self.get('var', 'cflags')
        c_includes = self.find_files('var', 'cincludes')

        if self.get("var", "trace"):
            trace_type = self.get('var', 'trace_type')
            if trace_type == 'vcd':
                ext = 'vcd'
                trace_opt = '--trace'
            elif trace_type == 'fst':
                ext = 'fst'
                trace_opt = '--trace-fst'
            else:
                raise ValueError("invalid trace type")

            options.append(trace_opt)

            # add siliconcompiler specific defines
            c_flags.append("-DSILICONCOMPILER_TRACE_DIR=\"reports\"")
            c_flags.append(
                f"-DSILICONCOMPILER_TRACE_FILE=\"reports/{self.design_topmodule}.{ext}\"")

        if c_includes:
            c_flags.extend([f'-I{include}' for include in c_includes])

        if c_flags:
            options.extend(['-CFLAGS', shlex.join(c_flags)])

        ld_flags = self.get('var', 'ldflags')
        if ld_flags:
            options.extend(['-LDFLAGS', shlex.join(ld_flags)])

        for lib, fileset in self.project.get_filesets():
            for value in lib.get_file(fileset=fileset, filetype="c"):
                options.append(value)

        return options
