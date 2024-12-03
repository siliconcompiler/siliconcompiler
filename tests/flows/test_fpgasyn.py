import json

import os

import siliconcompiler

import sys

import pytest

from siliconcompiler import FPGA
from siliconcompiler.targets import fpgaflow_demo
from siliconcompiler.utils import register_sc_data_source


####################################################
# Setup for test_fpgasyn Family FPGAs
####################################################
def setup():
    '''
    The test_fpgasyn FPGA family is designed specifically
    for testing FPGA synthesis flows
    '''

    arch_root = os.path.join('tests', 'flows', 'data', 'test_fpgasyn')

    lut_size = 4

    all_fpgas = []

    all_part_names = [
        'example_arch_test_fpgasyn',
    ]

    # Settings common to all parts in family
    for part_name in all_part_names:
        fpga = FPGA(part_name, package='siliconcompiler_data')
        register_sc_data_source(fpga)

        # Set the absolute minimum number of things needed to run
        # synthesis tests (add other properties as needed when writing new tests)

        fpga.set('fpga', part_name, 'lutsize', lut_size)
        fpga.add('fpga', part_name, 'var', 'feature_set', 'async_reset')
        fpga.add('fpga', part_name, 'var', 'feature_set', 'async_set')
        fpga.add('fpga', part_name, 'var', 'feature_set', 'enable')

        techlib_root = arch_root

        mae_library = os.path.join(techlib_root, 'tech_mae.v')
        fpga.add('fpga', part_name, 'file', 'yosys_extractlib', mae_library)
        fpga.add('fpga', part_name, 'file', 'yosys_macrolib', mae_library)

        all_fpgas.append(fpga)

    return all_fpgas


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.parametrize("top_module, expected_macro",
                         [('macc_pipe', 'efpga_mult'),
                          ('adder_extract', 'efpga_adder')])
def test_fpga_syn_extract(top_module,
                          expected_macro,
                          scroot,
                          arch_name='example_arch_test_fpgasyn'):

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('fpga', 'partname', arch_name)

    # This example architecture doesn't have a provided routing
    # graph file, so we don't have the metadata to to bitstream
    # generation.  Stop after routing instead of running to
    # completion.
    chip.set('option', 'to', ['syn'])

    flow_root = os.path.join(scroot, 'examples', 'fpga_flow')

    # 1. Defining the project
    # 2. Define source files
    v_src = os.path.join(flow_root, 'designs', top_module, f'{top_module}.v')
    chip.input(v_src)

    # 3. Load target
    chip.use(sys.modules[__name__])
    chip.use(fpgaflow_demo)

    assert chip.check_filepaths()

    chip.run()

    report_files = chip.find_files('tool', 'yosys', 'task', 'syn_fpga', 'report', 'luts',
                                   step='syn', index='0')
    file_found = False
    for report_file in report_files:
        if ('stat.json' in report_file):
            assert os.path.isfile(report_file)
            file_found = True

            with open(report_file, "r") as report_data:
                stats = json.loads(report_data.read())

                # In Yosys 0.44 at least, the stats are presented in two places.  One
                # is under a two-level keypath 'modules', '\\<top_module_name>';
                # and the other is at a top level key called 'design'
                # choose 'design' to key on so we're digging through one less
                # level of JSON dictionary hierarchy
                assert 'design' in stats, 'stats for top level "design" not found'

                design_stats = stats['design']

                # Breakdown of cell counts by type live within a key called
                # 'num_cells_by_type'

                assert 'num_cells_by_type' in design_stats, 'num_cells_by_type dictionary not found'

                cells_by_type = design_stats['num_cells_by_type']

                # Set up this test so that we are looking for exactly one
                # instance of a particular extracted macro

                assert expected_macro in cells_by_type, \
                    f'Expected macro {expected_macro} not found in cell types report'

                expected_macro_count = cells_by_type[expected_macro]

                assert expected_macro_count == 1, \
                    f'Expected one instance of {expected_macro},' \
                    ' got {expected_macro_count} instances'

    assert file_found, 'stat.json report file not found'
