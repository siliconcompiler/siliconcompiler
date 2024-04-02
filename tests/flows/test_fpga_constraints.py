import os

import pytest

import siliconcompiler

from siliconcompiler.targets import fpgaflow_demo


@pytest.mark.eda
@pytest.mark.quick
def test_fpga_constraints(scroot,
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

    # 3. Set placement constraints
    for i in range(8):
        chip.set('constraint', 'component', f'a[{i}]', 'placement', (0, 1, i))
        chip.set('constraint', 'component', f'b[{i}]', 'placement', (0, 2, i))
    for i in range(8):
        # ***NOTE: VPR prepends "out:" to the IO blocks that represent
        #          on-chip output locations, so we have to do that here
        #          in our constraints
        chip.set('constraint', 'component', f'out:y[{i}]', 'placement', (0, 3, i))
    chip.set('constraint', 'component', 'out:y[8]', 'placement', (1, 4, 0))

    # 4. Load target
    chip.load_target(fpgaflow_demo)

    chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


@pytest.mark.eda
@pytest.mark.quick
def test_fpga_pcf_constraints(scroot,
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
    json_constraints = os.path.join(flow_root,
                                    'designs',
                                    benchmark_name,
                                    'constraints',
                                    f'pin_constraints_{arch_name}.pcf')

    chip.input(json_constraints)

    # 4. Load target
    chip.load_target(fpgaflow_demo)

    chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


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

    chip.add('input', 'constraint', 'vpr_pins', xml_constraints)

    # 4. Load target
    chip.load_target(fpgaflow_demo)

    chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


if __name__ == "__main__":
    from tests.fixtures import scroot
    test_fpga_constraints(scroot())
