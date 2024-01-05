import os

import pytest

import siliconcompiler

from siliconcompiler.targets import fpgaflow_demo


@pytest.mark.eda
@pytest.mark.quick
def test_flopmap_fpgaflow(scroot,
                          arch_name='example_arch_X014Y014',
                          benchmark_name='updowncount',
                          top_module='updowncount'):

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('fpga', 'partname', arch_name)

    chip.set('option', 'to', ['route'])

    flow_root = os.path.join(scroot, 'examples', 'fpga_flow')

    # 1. Defining the project
    # 2. Define source files
    v_src = os.path.join(flow_root, 'designs', benchmark_name, f'{benchmark_name}.v')
    chip.input(v_src)

    # 3. Load target
    chip.load_target(fpgaflow_demo)

    chip.run()

    route_file = chip.find_result('route', step='route')

    assert os.path.exists(route_file)


if __name__ == "__main__":
    test_flopmap_fpgaflow()
