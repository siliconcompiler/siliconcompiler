import os
import json
import pytest
import siliconcompiler
from siliconcompiler.scheduler import _setup_node
from siliconcompiler.targets import fpgaflow_demo
from siliconcompiler.flows import fpgaflow
from siliconcompiler.tools.vpr import route, place
from siliconcompiler.flowgraph import _get_flowgraph_execution_order


@pytest.mark.eda
@pytest.mark.quick
def test_fpgaflow(scroot,
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
    chip.use(fpgaflow_demo)

    assert chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


@pytest.mark.eda
@pytest.mark.quick
def test_fpgaflow_apr(scroot,
                      arch_name='example_arch_X008Y008',
                      benchmark_name='adder',
                      top_module='adder'):

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('fpga', 'partname', arch_name)

    chip.set('option', 'to', ['route'])

    flow_root = os.path.join(scroot, 'examples', 'fpga_flow')

    # 1. Defining the project
    # 2. Define source files
    v_src = os.path.join(flow_root, 'designs', benchmark_name, f'{benchmark_name}.v')
    chip.input(v_src)

    # 3. Load target
    chip.use(fpgaflow_demo)

    assert chip.run()

    route_file = chip.find_result('route', step='route')

    assert os.path.exists(route_file)


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
    chip.use(fpgaflow_demo)

    assert chip.run()

    route_file = chip.find_result('route', step='route')

    screenshot_path = chip.show(route_file, screenshot=True)
    assert screenshot_path
    assert os.path.exists(screenshot_path)


@pytest.mark.eda
@pytest.mark.quick
def test_flopmap_fpgaflow(scroot,
                          arch_name='example_arch_X014Y014',
                          benchmark_name='updowncount',
                          top_module='updowncount'):

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('fpga', 'partname', arch_name)

    # This example architecture doesn't have a provided routing
    # graph file, so we don't have the metadata to to bitstream
    # generation.  Stop after routing instead of running to
    # completion.
    chip.set('option', 'to', ['route'])

    flow_root = os.path.join(scroot, 'examples', 'fpga_flow')

    # 1. Defining the project
    # 2. Define source files
    v_src = os.path.join(flow_root, 'designs', benchmark_name, f'{benchmark_name}.v')
    chip.input(v_src)

    # 3. Load target
    chip.use(fpgaflow_demo)

    assert chip.check_filepaths()

    assert chip.run()

    route_file = chip.find_result('route', step='route', index='0')
    assert route_file
    assert os.path.exists(route_file)


@pytest.mark.eda
@pytest.mark.quick
def test_dspmap_fpgaflow(scroot,
                         arch_name='example_arch_X014Y014',
                         benchmark_name='macc_pipe',
                         top_module='macc_pipe'):

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('fpga', 'partname', arch_name)

    # This example architecture doesn't have a provided routing
    # graph file, so we don't have the metadata to to bitstream
    # generation.  Stop after routing instead of running to
    # completion.
    chip.set('option', 'to', ['route'])

    flow_root = os.path.join(scroot, 'examples', 'fpga_flow')

    # 1. Defining the project
    # 2. Define source files
    v_src = os.path.join(flow_root, 'designs', benchmark_name, f'{benchmark_name}.v')
    chip.input(v_src)

    # 3. Load target
    chip.use(fpgaflow_demo)

    assert chip.check_filepaths()

    assert chip.run()

    route_file = chip.find_result('route', step='route', index='0')
    assert route_file
    assert os.path.exists(route_file)


@pytest.mark.eda
@pytest.mark.quick
def test_dspextract_fpgaflow(scroot,
                             arch_name='example_arch_X030Y030'):

    top_module = 'macc_pipe'

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('fpga', 'partname', arch_name)

    # This example architecture doesn't have a provided routing
    # graph file, so we don't have the metadata to to bitstream
    # generation.  Stop after routing instead of running to
    # completion.
    chip.set('option', 'to', ['route'])

    flow_root = os.path.join(scroot, 'examples', 'fpga_flow')

    # 1. Defining the project
    # 2. Define source files
    v_src = os.path.join(flow_root, 'designs', top_module, f'{top_module}.v')
    chip.input(v_src)

    # 3. Load target
    chip.use(fpgaflow_demo)

    assert chip.check_filepaths()

    assert chip.run()

    route_file = chip.find_result('route', step='route', index='0')
    assert route_file
    assert os.path.exists(route_file)


@pytest.mark.eda
@pytest.mark.quick
def test_dspblackbox_fpgaflow(scroot,
                              arch_name='example_arch_X030Y030'):

    top_module = 'macc'

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('fpga', 'partname', arch_name)

    # This example architecture doesn't have a provided routing
    # graph file, so we don't have the metadata to to bitstream
    # generation.  Stop after routing instead of running to
    # completion.
    chip.set('option', 'to', ['route'])

    flow_root = os.path.join(scroot, 'examples', 'fpga_flow')

    # 1. Defining the project
    # 2. Define source files
    v_src = os.path.join(flow_root, 'designs', top_module, f'{top_module}.v')
    chip.input(v_src)

    # 3. Load target
    chip.use(fpgaflow_demo)

    assert chip.check_filepaths()

    assert chip.run()

    route_file = chip.find_result('route', step='route', index='0')
    assert route_file
    assert os.path.exists(route_file)


@pytest.mark.eda
@pytest.mark.quick
def test_matrix_multiply_fpgaflow(scroot,
                                  arch_name='example_arch_X030Y030'):

    top_module = 'matrix_multiply'

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('fpga', 'partname', arch_name)

    # This example architecture doesn't have a provided routing
    # graph file, so we don't have the metadata to to bitstream
    # generation.  Stop after routing instead of running to
    # completion.
    chip.set('option', 'to', ['route'])

    flow_root = os.path.join(scroot, 'examples', 'fpga_flow')

    # 1. Defining the project
    # 2. Define source files
    v_src = [
        os.path.join(flow_root, 'designs', top_module, f'{top_module}.v'),
        os.path.join(flow_root, 'designs', top_module, 'matrix_multiply_control.v'),
        os.path.join(flow_root, 'designs', top_module, 'row_col_data_mux.v'),
        os.path.join(flow_root, 'designs', top_module, 'row_col_memory.v'),
        os.path.join(flow_root, 'designs', top_module, 'row_col_multiply.v'),
        os.path.join(flow_root, 'designs', top_module, 'row_col_product_adder.v'),
    ]
    for src in v_src:
        chip.input(src)

    # 3. Load target
    chip.use(fpgaflow_demo)

    assert chip.check_filepaths()

    assert chip.run()

    route_file = chip.find_result('route', step='route', index='0')
    assert route_file
    assert os.path.exists(route_file)


@pytest.mark.eda
@pytest.mark.quick
def test_mem_to_flops_fpgaflow(scroot,
                               arch_name='example_arch_X030Y030',
                               benchmark_name='register_file',
                               top_module='register_file'):

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('fpga', 'partname', arch_name)

    # This example architecture doesn't have a provided routing
    # graph file, so we don't have the metadata to to bitstream
    # generation.  Stop after routing instead of running to
    # completion.
    chip.set('option', 'to', ['route'])

    flow_root = os.path.join(scroot, 'examples', 'fpga_flow')

    # 1. Defining the project
    # 2. Define source files
    v_src = os.path.join(flow_root, 'designs', benchmark_name, f'{benchmark_name}.v')
    chip.input(v_src)

    # 3. Load target
    chip.use(fpgaflow_demo)

    assert chip.check_filepaths()

    chip.set('option', 'quiet', True)
    assert chip.run()

    route_file = chip.find_result('route', step='route', index='0')
    assert route_file
    assert os.path.exists(route_file)


@pytest.mark.eda
@pytest.mark.quick
def test_fpgaflow_vhdl(scroot,
                       arch_name='example_arch_X005Y005',
                       benchmark_name='adder',
                       top_module='adder'):

    chip = siliconcompiler.Chip(f'{top_module}')

    chip.set('fpga', 'partname', arch_name)

    flow_root = os.path.join(scroot, 'examples', 'fpga_flow')

    # 1. Defining the project
    # 2. Define source files
    v_src = os.path.join(flow_root, 'designs', benchmark_name, f'{benchmark_name}.vhd')
    chip.input(v_src)

    # 3. Load target
    chip.use(fpgaflow_demo)

    assert chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


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
        place.add_placement_constraint(chip, f'a[{i}]', (0, 1, i))
        place.add_placement_constraint(chip, f'b[{i}]', (0, 2, i))
    for i in range(8):
        # ***NOTE: VPR prepends "out:" to the IO blocks that represent
        #          on-chip output locations, so we have to do that here
        #          in our constraints
        place.add_placement_constraint(chip, f'out:y[{i}]', (0, 3, i))
    place.add_placement_constraint(chip, 'out:y[8]', (1, 4, 0))

    # 4. Load target
    chip.use(fpgaflow_demo)

    assert chip.run()

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
    chip.use(fpgaflow_demo)

    assert chip.run()

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
    chip.use(fpgaflow_demo)

    assert chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


def test_vpr_max_router_iterations(scroot,
                                   part_name="example_arch_X008Y008"):

    chip = siliconcompiler.Chip('foo')
    chip.input('test.v')

    chip.set('fpga', 'partname', part_name)

    test_value = '300'

    chip.set('tool', 'vpr', 'task', 'route', 'var', 'max_router_iterations', test_value)

    # 3. Load target
    chip.use(fpgaflow_demo)

    # Verify that the user's setting doesn't get clobbered
    # by the FPGA flow
    for layer_nodes in _get_flowgraph_execution_order(chip, 'fpgaflow'):
        for step, index in layer_nodes:
            _setup_node(chip, step, index)

    assert test_value == \
        chip.get('tool', 'vpr', 'task', 'route', 'var', 'max_router_iterations',
                 step='route', index='0')[0]

    chip.set('arg', 'step', 'route')
    chip.set('arg', 'index', '0')
    assert f'--max_router_iterations {test_value}' in route.runtime_options(chip)


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.parametrize("top_module, expected_macro",
                         [('macc_pipe', 'efpga_mult'),
                          ('adder_extract', 'efpga_adder')])
def test_fpga_syn_extract(top_module,
                          expected_macro,
                          datadir):

    # Build FPGA
    arch_name = 'example_arch_test_fpgasyn'

    fpga = siliconcompiler.FPGA(arch_name)

    # Set the absolute minimum number of things needed to run
    # synthesis tests (add other properties as needed when writing new tests)

    fpga.set('fpga', arch_name, 'lutsize', 4)
    fpga.add('fpga', arch_name, 'var', 'feature_set', 'async_reset')
    fpga.add('fpga', arch_name, 'var', 'feature_set', 'async_set')
    fpga.add('fpga', arch_name, 'var', 'feature_set', 'enable')

    techlib_root = os.path.join(datadir, 'test_fpgasyn')

    mae_library = os.path.join(techlib_root, 'tech_mae.v')
    fpga.add('fpga', arch_name, 'file', 'yosys_extractlib', mae_library)
    fpga.add('fpga', arch_name, 'file', 'yosys_macrolib', mae_library)

    # Setup chip
    chip = siliconcompiler.Chip(top_module)

    chip.set('fpga', 'partname', arch_name)

    chip.set('option', 'to', 'syn')

    # 1. Defining the project
    # 2. Define source files
    chip.input(os.path.join(datadir, 'fpga_designs', f'{top_module}.v'))

    # 3. Load target
    chip.use(fpga)
    chip.use(fpgaflow, fpgaflow_type='vpr')

    # 4. Select default flow
    chip.set('option', 'flow', 'fpgaflow')

    assert chip.check_filepaths()

    assert chip.run()

    report_file = f'build/{top_module}/job0/syn/0/reports/stat.json'
    assert os.path.isfile(report_file)

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


if __name__ == "__main__":
    from tests.fixtures import scroot
    test_fpgaflow(scroot)
