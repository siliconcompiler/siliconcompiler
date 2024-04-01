import os

import pytest

import siliconcompiler

from siliconcompiler.targets import fpgaflow_demo


@pytest.mark.eda
@pytest.mark.quick
def test_fpga_xml_constraints(scroot,
                              arch_name='example_arch_X014Y014',
                              benchmark_name='adder',
                              top_module='adder'):

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('fpga', 'partname', arch_name)

    flow_root = os.path.join(scroot, 'examples', 'fpga_flow')

    # 1. Defining the project
    # 2. Define source files
    v_src = os.path.join(flow_root, 'designs', benchmark_name, f'{benchmark_name}.v')
    chip.input(v_src)

    # 3. Set placement constraints
    xml_constraints = os.path.join(scroot,
                                   'tests',
                                   'flows',
                                   'data',
                                   'test_fpgaflow',
                                   f'pin_constraints_{arch_name}.xml')

    chip.add('input', 'constraint', 'pins', xml_constraints)

    # 4. Load target
    chip.load_target(fpgaflow_demo)

    chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


if __name__ == "__main__":
    from tests.fixtures import scroot
    test_fpga_xml_constraints(scroot())
