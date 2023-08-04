import os

import pytest

import siliconcompiler

from siliconcompiler.targets import fpgaflow_demo


@pytest.mark.eda
@pytest.mark.quick
def test_fpgaflow(scroot,
                  arch_name='example_arch_X005Y005',
                  benchmark_name='adder',
                  top_module='adder'):

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('option', 'frontend', 'vhdl')

    chip.set('option', 'fpga', arch_name)

    flow_root = os.path.join(scroot, 'examples', 'fpga_flow')

    # 1. Defining the project
    # 2. Define source files
    v_src = os.path.join(flow_root, 'designs', benchmark_name, f'{benchmark_name}.vhd')
    chip.input(v_src)

    # 3. Load target
    chip.load_target(fpgaflow_demo)

    chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


if __name__ == "__main__":
    test_fpgaflow(os.environ['SCPATH'])
