import shlex

from siliconcompiler.tools.verilator.compile import CompileTask
from siliconcompiler.tools._common.cocotb.cocotb_task import (
    get_cocotb_config
)


class CocotbCompileTask(CompileTask):

    @classmethod
    def framework_distributions(cls):
        """cocotb: the simulation links its VPI library from the copy the
        node's image holds, at SiliconCompiler's range."""
        return ("cocotb",)

    def task(self):
        return "cocotb_compile"

    def _setup_c_file_requirement(self):
        pass

    def runtime_options(self):
        options = super().runtime_options()

        # Cocotb-specific flags
        options.append('--vpi')
        options.append('--public-flat-rw')
        options.extend(['--prefix', 'Vtop'])

        # Get cocotb configuration
        libs_dir, vpi_lib, share_dir = get_cocotb_config("verilator")

        # Link flags for cocotb VPI library
        # The library file is like "libcocotbvpi_verilator.so", but -l expects
        # "cocotbvpi_verilator", so strip the "lib" prefix and the suffix.
        link_name = vpi_lib.stem

        if link_name.startswith('lib'):
            link_name = link_name[3:]
        else:
            raise RuntimeError(f"Unexpected cocotb VPI library name: {vpi_lib.name}")

        cocotb_flags = [
            f'-Wl,-rpath,{libs_dir}',
            f'-L{libs_dir}',
            f'-l{link_name}'
        ]

        options.extend(['-LDFLAGS', shlex.join(cocotb_flags)])

        # Add cocotb's verilator.cpp as the simulation main
        verilator_cpp = f'{share_dir}/lib/verilator/verilator.cpp'
        options.append(verilator_cpp)

        return options
