import os

import pytest

import siliconcompiler

from siliconcompiler.targets import fpga_vpr_flow_demo


@pytest.mark.eda
@pytest.mark.quick
def test_fpgaflow(scroot,
                  route_chan_width=32,
                  lut_size=4,
                  arch_name='example_arch_X005Y005',
                  benchmark_name='adder',
                  top_module='adder'):

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('option', 'frontend', 'vhdl')

    chip.set('fpga', 'partname', arch_name)

    flow_root = os.path.join(scroot, 'examples', 'fpga_flow')
    arch_root = os.path.join(flow_root, 'arch', arch_name)

    # 1. Defining the project
    # 2. Define source files
    v_src = os.path.join(flow_root, 'designs', benchmark_name, f'{benchmark_name}.vhd')
    chip.input(v_src)

    # 3.  Synthesis Setup

    # 4.  VPR Setup
    xml_file = os.path.join(arch_root, f'{arch_name}.xml')
    rr_graph_file = os.path.join(arch_root, f'{arch_name}_rr_graph.xml')

    chip.set('fpga', 'arch', xml_file)
    # ***NOTE:  If the RR graph is not specified, the FASM bitstream will
    #           generate but omit any bitstream data for programmable
    #           interconnect (SBs and CBs); meaning that the FPGA will
    #           not be correctly programmed. -PG 5/17/2023
    chip.set('tool', 'vpr', 'task', 'apr', 'var', 'rr_graph', f'{rr_graph_file}')
    chip.set('tool', 'vpr', 'task', 'apr', 'var', 'route_chan_width', f'{route_chan_width}')

    # 5. Load target
    chip.load_target(fpga_vpr_flow_demo)

    # 6. Set flow

    chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert fasm_file.endswith(f'{top_module}.fasm')


if __name__ == "__main__":
    test_fpgaflow(os.environ['SCPATH'])
