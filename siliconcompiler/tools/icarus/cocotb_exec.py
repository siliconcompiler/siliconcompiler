from siliconcompiler.tools._common.cocotb.cocotb_task import (
    CocotbTask,
    get_cocotb_config
)


class CocotbExecTask(CocotbTask):
    '''
    Run a cocotb testbench against a compiled Icarus Verilog simulation.

    This task takes a compiled .vvp file from the icarus compile task and
    executes it with the cocotb VPI module loaded, enabling Python-based
    testbenches to interact with the simulation.

    The task requires cocotb to be installed in the Python environment.
    Test modules are specified by adding Python files to the fileset using
    the "python" filetype.
    '''

    def tool(self):
        return "icarus"

    def parse_version(self, stdout):
        # vvp version output: "Icarus Verilog runtime version 13.0 (devel) ..."
        return stdout.split()[4]

    def setup(self):
        super().setup()

        # vvp is the Icarus Verilog runtime
        self.set_exe("vvp", vswitch="-V")
        self.add_version(">=10.3")

        self.set_threads()

        # Input: compiled .vvp file from compile task
        self.add_input_file(ext="vvp")

    def runtime_options(self):
        options = super().runtime_options()

        libs_dir, lib_name, _ = get_cocotb_config("icarus")

        # -M: VPI module search path
        options.extend(["-M", str(libs_dir)])

        # -m: VPI module to load
        options.extend(["-m", lib_name])

        # Input .vvp file
        options.append(f"inputs/{self.design_topmodule}.vvp")

        return options
