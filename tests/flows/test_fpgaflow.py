import os
import shutil

import pytest

import siliconcompiler


@pytest.mark.eda
@pytest.mark.quick
def test_fpgaflow(scroot,
                  route_chan_width=100,
                  lut_size=5,
                  benchmark_name='and_latch',
                  top_module='and_latch'):

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('fpga', 'partname', 'k6_frac_N10_40nm')

    vpr_path = shutil.which('vpr')
    vpr_root = vpr_path[:-8]

    # single_port_ram_stub = os.path.join(scroot,
    #                                    'siliconcompiler',
    #                                    'tools',
    #                                    'yosys',
    #                                    'vpr_yosysstubs',
    #                                    'single_port_ram.v')

    # dual_port_ram_stub = os.path.join(scroot,
    #                                  'siliconcompiler',
    #                                  'tools',
    #                                  'yosys',
    #                                  'vpr_yosysstubs',
    #                                  'dual_port_ram.v')

    # 1. Defining the project
    # 2. Define source files
    v_src = os.path.join(vpr_root, 'vtr_flow', 'benchmarks', 'verilog', f'{benchmark_name}.v')
    chip.input(v_src)
    # chip.input(single_port_ram_stub)
    # chip.input(dual_port_ram_stub)

    # 3.  Synthesis Setup
    # single_port_ram_lib = os.path.join(scroot,
    #                                    'siliconcompiler',
    #                                   'tools',
    #                                   'yosys',
    #                                   'vpr_yosyslib',
    #                                   'single_port_ram.v')

    # dual_port_ram_lib = os.path.join(scroot,
    #                                 'siliconcompiler',
    #                                 'tools',
    #                                 'yosys',
    #                                 'vpr_yosyslib',
    #                                 'dual_port_ram.v')

    chip.add('tool', 'yosys', 'task', 'syn', 'var', 'lut_size', f'{lut_size}')
    chip.add('tool', 'yosys', 'task', 'syn', 'var', 'memmap', 'None')
    chip.add('tool', 'yosys', 'task', 'syn', 'var', 'techmap', 'None')
    # chip.add('tool', 'yosys', 'task', 'syn', 'var', 'techmap', single_port_ram_lib)
    # chip.add('tool', 'yosys', 'task', 'syn', 'var', 'techmap', dual_port_ram_lib)
    chip.add('tool', 'yosys', 'task', 'syn', 'var', 'techmap_define', 'MEM_MAXADDR=14')

    # 4.  VPR Setup
    # xml_file = os.path.join(vpr_root, 'vtr_flow', 'arch', 'timing', 'k6_frac_N10_mem32K_40nm.xml')
    xml_file = os.path.join(vpr_root, 'utils', 'fasm', 'test', 'test_fasm_arch.xml')

    chip.set('fpga', 'arch', xml_file)
    chip.set('tool', 'vpr', 'task', 'apr', 'var', 'route_chan_width', f'{route_chan_width}')

    # 5. Load target
    chip.load_target('fpgaflow_demo')

    # 6. Set flow

    chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert fasm_file.endswith(f'{top_module}.fasm')
