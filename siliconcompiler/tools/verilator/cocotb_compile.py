import shlex

from siliconcompiler.tools.verilator.compile import CompileTask
from siliconcompiler.tools._common.cocotb.cocotb_task import (
    get_cocotb_config
)


class CocotbCompileTask(CompileTask):

    def __init__(self):
        super().__init__()

    def task(self):
        return "cocotb_compile"

    def tool(self):
        return super().tool()

    def setup(self):
        super().setup()

    def _setup_c_file_requirement(self):
        pass

    def runtime_options(self):
        options = super().runtime_options()

        # Cocotb-specific flags
        options.append('--vpi')
        options.append('--public-flat-rw')
        options.extend(['--prefix', 'Vtop'])

        # Get cocotb configuration
        libs_dir, lib_name, share_dir = get_cocotb_config("verilator")

        # Link flags for cocotb VPI library
        # lib_name is like "libcocotbvpi_verilator.so", but -l expects "cocotbvpi_verilator"
        # Strip "lib" prefix and ".so" suffix
        link_name = lib_name
        if link_name.startswith('lib'):
            link_name = link_name[3:]
        if link_name.endswith('.so'):
            link_name = link_name[:-3]

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
