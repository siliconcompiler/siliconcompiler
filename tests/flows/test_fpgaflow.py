import os
import json
import pytest
import time
from siliconcompiler import Chip, FPGA
from siliconcompiler.scheduler.schedulernode import SchedulerNode
from siliconcompiler.flows import fpgaflow
from siliconcompiler.tools.vpr import route, place
from logiklib.demo.K4_N8_6x6 import K4_N8_6x6
from logiklib.demo.K6_N8_3x3 import K6_N8_3x3
from logiklib.demo.K6_N8_12x12_BD import K6_N8_12x12_BD
from logiklib.demo.K6_N8_28x28_BD import K6_N8_28x28_BD


@pytest.fixture
def designs_dir(datadir):
    return os.path.join(datadir, 'fpga_designs')


@pytest.fixture(autouse=True, scope="module")
def load_archs():
    pytest.skip("Downloading artifacts are way too unstable")
    for lib in [K4_N8_6x6, K6_N8_3x3, K6_N8_12x12_BD, K6_N8_28x28_BD]:
        chip = Chip("dummy")
        chip.use(lib)
        assert chip.check_filepaths()
        time.sleep(10)


@pytest.mark.eda
@pytest.mark.quick
def test_fpgaflow(designs_dir):
    chip = Chip("adder")

    # 1. Defining the project
    chip.use(K6_N8_3x3)
    chip.set('fpga', 'partname', 'K6_N8_3x3')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "adder.v"))

    # 3. Load flow
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

    assert chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


@pytest.mark.eda
@pytest.mark.quick
def test_fpgaflow_apr(designs_dir):
    chip = Chip("adder")

    # 1. Defining the project
    chip.use(K4_N8_6x6)
    chip.set('fpga', 'partname', 'K4_N8_6x6')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "adder.v"))

    # 3. Load flow
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

    chip.set('option', 'to', 'route')

    assert chip.run()

    route_file = chip.find_result('route', step='route')

    assert os.path.exists(route_file)


@pytest.mark.eda
@pytest.mark.quick
def test_fpgaflow_screenshot(designs_dir):
    chip = Chip("adder")

    # 1. Defining the project
    chip.use(K6_N8_3x3)
    chip.set('fpga', 'partname', 'K6_N8_3x3')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "adder.v"))

    # 3. Load flow
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

    assert chip.run()

    route_file = chip.find_result('route', step='route')

    screenshot_path = chip.show(route_file, screenshot=True)
    assert screenshot_path
    assert os.path.exists(screenshot_path)


@pytest.mark.eda
@pytest.mark.quick
def test_flopmap_fpgaflow(designs_dir):
    chip = Chip("updowncount")

    # 1. Defining the project
    chip.use(K6_N8_12x12_BD)
    chip.set('fpga', 'partname', 'K6_N8_12x12_BD')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "updowncount.v"))

    # 3. Load flow
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

    # This example architecture doesn't have a provided routing
    # graph file, so we don't have the metadata to to bitstream
    # generation.  Stop after routing instead of running to
    # completion.
    chip.set('option', 'to', 'route')

    assert chip.check_filepaths()

    assert chip.run()

    route_file = chip.find_result('route', step='route', index='0')
    assert route_file
    assert os.path.exists(route_file)


@pytest.mark.eda
@pytest.mark.quick
def test_dspmap_fpgaflow(designs_dir):
    chip = Chip('macc_pipe')

    # 1. Defining the project
    chip.use(K6_N8_12x12_BD)
    chip.set('fpga', 'partname', 'K6_N8_12x12_BD')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "macc_pipe.v"))

    # 3. Load flow
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

    # This example architecture doesn't have a provided routing
    # graph file, so we don't have the metadata to to bitstream
    # generation.  Stop after routing instead of running to
    # completion.
    chip.set('option', 'to', 'route')

    assert chip.check_filepaths()

    assert chip.run()

    route_file = chip.find_result('route', step='route', index='0')
    assert route_file
    assert os.path.exists(route_file)


@pytest.mark.eda
@pytest.mark.quick
def test_dspextract_fpgaflow(designs_dir):
    chip = Chip('macc_pipe')

    # 1. Defining the project
    chip.use(K6_N8_28x28_BD)
    chip.set('fpga', 'partname', 'K6_N8_28x28_BD')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "macc_pipe.v"))

    # 3. Load flow
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

    # This example architecture doesn't have a provided routing
    # graph file, so we don't have the metadata to to bitstream
    # generation.  Stop after routing instead of running to
    # completion.
    chip.set('option', 'to', 'route')

    assert chip.check_filepaths()

    assert chip.run()

    route_file = chip.find_result('route', step='route', index='0')
    assert route_file
    assert os.path.exists(route_file)


@pytest.mark.eda
@pytest.mark.quick
def test_dspblackbox_fpgaflow(designs_dir):
    chip = Chip('macc')

    # 1. Defining the project
    chip.use(K6_N8_28x28_BD)
    chip.set('fpga', 'partname', 'K6_N8_28x28_BD')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "macc.v"))

    # 3. Load flow
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

    # This example architecture doesn't have a provided routing
    # graph file, so we don't have the metadata to to bitstream
    # generation.  Stop after routing instead of running to
    # completion.
    chip.set('option', 'to', 'route')

    assert chip.check_filepaths()

    assert chip.run()

    route_file = chip.find_result('route', step='route', index='0')
    assert route_file
    assert os.path.exists(route_file)


@pytest.mark.eda
@pytest.mark.quick
def test_matrix_multiply_fpgaflow(designs_dir):

    chip = Chip('matrix_multiply')

    # 1. Defining the project
    chip.use(K6_N8_28x28_BD)
    chip.set('fpga', 'partname', 'K6_N8_28x28_BD')

    # 2. Define source files
    for src in (os.path.join(designs_dir, 'matrix_multiply', 'matrix_multiply.v'),
                os.path.join(designs_dir, 'matrix_multiply', 'matrix_multiply_control.v'),
                os.path.join(designs_dir, 'matrix_multiply', 'row_col_data_mux.v'),
                os.path.join(designs_dir, 'matrix_multiply', 'row_col_memory.v'),
                os.path.join(designs_dir, 'matrix_multiply', 'row_col_multiply.v'),
                os.path.join(designs_dir, 'matrix_multiply', 'row_col_product_adder.v')):
        chip.input(src)

    # 3. Load flow
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

    # This example architecture doesn't have a provided routing
    # graph file, so we don't have the metadata to to bitstream
    # generation.  Stop after routing instead of running to
    # completion.
    chip.set('option', 'to', 'route')

    assert chip.check_filepaths()

    assert chip.run()

    route_file = chip.find_result('route', step='route', index='0')
    assert route_file
    assert os.path.exists(route_file)


@pytest.mark.eda
@pytest.mark.quick
def test_mem_to_flops_fpgaflow(designs_dir):
    chip = Chip('register_file')

    # 1. Defining the project
    chip.use(K6_N8_28x28_BD)
    chip.set('fpga', 'partname', 'K6_N8_28x28_BD')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "register_file.v"))

    # 3. Load flow
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

    # This example architecture doesn't have a provided routing
    # graph file, so we don't have the metadata to to bitstream
    # generation.  Stop after routing instead of running to
    # completion.
    chip.set('option', 'to', 'route')

    assert chip.check_filepaths()

    chip.set('option', 'quiet', True)
    assert chip.run()

    route_file = chip.find_result('route', step='route', index='0')
    assert route_file
    assert os.path.exists(route_file)


@pytest.mark.eda
@pytest.mark.quick
def test_fpgaflow_vhdl(designs_dir):
    chip = Chip('adder')

    # 1. Defining the project
    chip.use(K6_N8_3x3)
    chip.set('fpga', 'partname', 'K6_N8_3x3')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "adder.vhd"))

    # 3. Load flow
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

    assert chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


@pytest.mark.eda
@pytest.mark.quick
def test_fpga_constraints(designs_dir):
    chip = Chip('adder')

    # 1. Defining the project
    chip.use(K6_N8_3x3)
    chip.set('fpga', 'partname', 'K6_N8_3x3')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "adder.v"))

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

    # 4. Load flow
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

    assert chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


@pytest.mark.eda
@pytest.mark.quick
def test_fpga_pcf_constraints(designs_dir):
    chip = Chip('adder')

    # 1. Defining the project
    chip.use(K6_N8_12x12_BD)
    chip.set('fpga', 'partname', 'K6_N8_12x12_BD')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "adder.v"))

    # 3. Set placement constraints
    chip.input(os.path.join(designs_dir, "adder_pin_constraints_K6_N8_12x12_BD.pcf"))

    # 4. Load flow
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

    assert chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


@pytest.mark.eda
@pytest.mark.quick
def test_fpga_xml_constraints(designs_dir, datadir):
    chip = Chip('adder')

    # 1. Defining the project
    chip.use(K6_N8_12x12_BD)
    chip.set('fpga', 'partname', 'K6_N8_12x12_BD')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "adder.v"))

    # 3. Set placement constraints
    chip.add('input', 'constraint', 'vpr_pins',
             os.path.join(datadir, 'test_fpgaflow', 'pin_constraints_K6_N8_12x12_BD.xml'))

    # 4. Load flow
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

    assert chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


def test_vpr_max_router_iterations():
    chip = Chip('foo')
    chip.input('test.v')

    part_name = 'faux'

    # Create FPGA
    fpga = FPGA(part_name)

    fpga.set('fpga', part_name, 'var', 'vpr_device_code', 'faux')
    fpga.set('fpga', part_name, 'var', 'vpr_clock_model', 'ideal')

    with open('test.file', 'w') as f:
        f.write('test')

    fpga.set('fpga', part_name, 'file', 'archfile', 'test.file')
    fpga.set('fpga', part_name, 'file', 'graphfile', 'test.file')

    fpga.set('fpga', part_name, 'var', 'channelwidth', 50)

    chip.use(fpga)
    chip.set('fpga', 'partname', 'faux')

    # 3. Load flow
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

    chip.set('tool', 'vpr', 'task', 'route', 'var', 'max_router_iterations', 300)

    # Verify that the user's setting doesn't get clobbered
    # by the FPGA flow
    for layer_nodes in chip.get(
            "flowgraph", "fpgaflow", field="schema").get_execution_order():
        for step, index in layer_nodes:
            SchedulerNode(chip, step, index).setup()

    assert '300' == \
        chip.get('tool', 'vpr', 'task', 'route', 'var', 'max_router_iterations',
                 step='route', index='0')[0]

    chip.set('arg', 'step', 'route')
    chip.set('arg', 'index', '0')
    assert '--max_router_iterations' in route.runtime_options(chip)
    assert '300' in route.runtime_options(chip)


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

    fpga = FPGA(arch_name)

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
    chip = Chip(top_module)

    chip.set('fpga', 'partname', arch_name)

    chip.set('option', 'to', 'syn')

    # 1. Defining the project
    # 2. Define source files
    chip.input(os.path.join(datadir, 'fpga_designs', f'{top_module}.v'))

    # 3. Load flow
    chip.use(fpga)
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

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


def test_vpr_gen_post_implementation_netlist():
    chip = Chip('foo')
    chip.input('test.v')

    part_name = 'faux'

    # Create FPGA
    fpga = FPGA(part_name)

    fpga.set('fpga', part_name, 'var', 'vpr_device_code', 'faux')
    fpga.set('fpga', part_name, 'var', 'vpr_clock_model', 'ideal')

    with open('test.file', 'w') as f:
        f.write('test')

    fpga.set('fpga', part_name, 'file', 'archfile', 'test.file')
    fpga.set('fpga', part_name, 'file', 'graphfile', 'test.file')

    fpga.set('fpga', part_name, 'var', 'channelwidth', 50)

    chip.use(fpga)
    chip.set('fpga', 'partname', 'faux')

    # 3. Load flow
    chip.use(fpgaflow, fpgaflow_type='vpr')
    chip.set('option', 'flow', 'fpgaflow')

    chip.set('tool', 'vpr', 'task', 'route', 'var', 'gen_post_implementation_netlist', True)
    chip.set('tool', 'vpr', 'task', 'route', 'var', 'timing_corner', 'slow')

    # Verify that the user's setting doesn't get clobbered
    # by the FPGA flow
    for layer_nodes in chip.get(
            "flowgraph", "fpgaflow", field="schema").get_execution_order():
        for step, index in layer_nodes:
            SchedulerNode(chip, step, index).setup()

    assert 'true' == \
        chip.get('tool', 'vpr', 'task', 'route', 'var', 'gen_post_implementation_netlist',
                 step='route', index='0')[0]
    assert 'slow' == \
        chip.get('tool', 'vpr', 'task', 'route', 'var', 'timing_corner',
                 step='route', index='0')[0]

    node = SchedulerNode(chip, step='route', index='0')
    with node.runtime():
        assert '--gen_post_synthesis_netlist' in node.task.get_runtime_arguments()
