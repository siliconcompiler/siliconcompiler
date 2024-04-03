import os

import pytest

import siliconcompiler

from siliconcompiler.targets import fpgaflow_demo


@pytest.mark.eda
@pytest.mark.quick
def test_fpgaflow_screenshot(scroot,
                             arch_name='example_arch_X005Y005',
                             benchmark_name='adder',
                             top_module='adder'):

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('fpga', 'partname', arch_name)

    flow_root = os.path.join(scroot, 'examples', 'fpga_flow')

    # 1. Defining the project
    # 2. Define source files
    v_src = os.path.join(flow_root, 'designs', benchmark_name, f'{benchmark_name}.v')
    chip.input(v_src)

    # 3. Load target
    chip.load_target(fpgaflow_demo)

    chip.run()

    route_file = chip.find_result('route', step='route')

    screenshot_path = chip.show(route_file, screenshot=True)
    assert screenshot_path
    assert os.path.exists(screenshot_path)


if __name__ == "__main__":
    from tests.fixtures import scroot
    test_fpgaflow_screenshot(scroot)
