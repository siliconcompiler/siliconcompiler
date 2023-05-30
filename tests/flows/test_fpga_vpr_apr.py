import os

import pytest

import siliconcompiler


@pytest.mark.eda
@pytest.mark.quick
def test_fpga_vpr_apr(scroot,
                      route_chan_width=32,
                      lut_size=4,
                      arch_name='zafg000sc_X005Y005',
                      benchmark_name='adder',
                      top_module='adder'):

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('fpga', 'partname', arch_name)

    chip.set('option', 'steplist', ['import', 'syn', 'place', 'route'])

    flow_root = os.path.join(scroot, 'examples', 'fpga_flow')
    arch_root = os.path.join(flow_root, 'arch', arch_name)

    # 1. Defining the project
    # 2. Define source files
    v_src = os.path.join(flow_root, 'designs', benchmark_name, f'{benchmark_name}.v')
    chip.input(v_src)

    # 3.  Synthesis Setup

    chip.add('tool', 'yosys', 'task', 'syn', 'var', 'lut_size', f'{lut_size}')
    chip.add('tool', 'yosys', 'task', 'syn', 'var', 'memmap', 'None')
    chip.add('tool', 'yosys', 'task', 'syn', 'var', 'techmap', 'None')

    # 4.  VPR Setup
    xml_file = os.path.join(arch_root, f'{arch_name}.xml')

    chip.set('fpga', 'arch', xml_file)
    chip.set('tool', 'vpr', 'task', 'apr', 'var', 'route_chan_width', f'{route_chan_width}')

    # 5. Load target
    chip.load_target('fpga_vpr_flow_demo')

    # 6. Set flow

    chip.run()

    route_file = chip.find_result('route', step='route')

    assert route_file.endswith(f'{top_module}.route')


if __name__ == "__main__":
    test_fpga_vpr_apr(os.environ['SCPATH'])
