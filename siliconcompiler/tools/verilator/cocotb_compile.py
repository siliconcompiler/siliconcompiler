import shlex
from typing import Optional, List, Union

from siliconcompiler.tools.verilator import VerilatorTask


class CocotbCompileTask(VerilatorTask):
    '''
    Compiles Verilog sources into an executable with cocotb VPI support.

    This task extends the standard Verilator compile task to include the
    necessary flags and libraries for cocotb integration:

    - Enables VPI interface (--vpi)
    - Makes all signals accessible to VPI (--public-flat-rw)
    - Links against cocotb's VPI library (libcocotbvpi_verilator)
    - Includes cocotb's verilator.cpp as the simulation main

    Outputs an executable to ``outputs/<design>.vexe``.
    '''

    def __init__(self):
        super().__init__()

        self.add_parameter("mode", "<cc,systemc>", "defines compilation mode for Verilator",
                           defvalue="cc")
        self.add_parameter("trace", "bool", "if true, enables trace generation")
        self.add_parameter("trace_type", "<vcd,fst>",
                           "specifies type of wave file to create when [trace] is set",
                           defvalue="vcd")

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
        return "cocotb_compile"

    def _get_cocotb_config(self):
        """
        Import and return cocotb configuration.

        Returns:
            tuple: (libs_dir, lib_name, share_dir, libpython_path)

        Raises:
            ImportError: If cocotb_tools is not installed.
        """
        try:
            import cocotb_tools.config
            import find_libpython

            libs_dir = cocotb_tools.config.libs_dir
            lib_name = cocotb_tools.config.lib_name("vpi", "verilator")
            share_dir = cocotb_tools.config.share_dir
            libpython_path = find_libpython.find_libpython()

            if not libpython_path:
                raise ValueError(
                    "Unable to find libpython. Please ensure libpython is installed."
                )

            return libs_dir, lib_name, share_dir, libpython_path
        except ImportError as e:
            raise ImportError(
                "cocotb must be installed to use the cocotb compile task. "
                "Install it with: pip install cocotb"
            ) from e

    def setup(self):
        super().setup()
        self.set_threads()

        self.add_output_file(ext="vexe")

        # Mark required
        self.add_required_key("var", "mode")
        self.add_required_key("var", "trace")
        self.add_required_key("var", "trace_type")
        self.add_required_key("var", "initialize_random")

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

        # Cocotb-specific flags
        options.append('--vpi')
        options.append('--public-flat-rw')
        options.extend(['--prefix', 'Vtop'])

        options.extend(['-o', f'../outputs/{self.design_topmodule}.vexe'])

        c_flags = self.get('var', 'cflags')
        c_includes = self.find_files('var', 'cincludes')

        # Get cocotb configuration
        libs_dir, lib_name, share_dir, _ = self._get_cocotb_config()

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

        # Link flags for cocotb VPI library
        # lib_name is like "libcocotbvpi_verilator.so", but -l expects "cocotbvpi_verilator"
        # Strip "lib" prefix and ".so" suffix
        link_name = lib_name
        if link_name.startswith('lib'):
            link_name = link_name[3:]
        if link_name.endswith('.so'):
            link_name = link_name[:-3]

        ld_flags = self.get('var', 'ldflags')
        ld_flags.extend([
            f'-Wl,-rpath,{libs_dir}',
            f'-L{libs_dir}',
            f'-l{link_name}'
        ])
        options.extend(['-LDFLAGS', shlex.join(ld_flags)])

        # Add cocotb's verilator.cpp as the simulation main
        verilator_cpp = f'{share_dir}/lib/verilator/verilator.cpp'
        options.append(verilator_cpp)

        return options
