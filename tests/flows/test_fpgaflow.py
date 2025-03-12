import os
import json
import pytest
from siliconcompiler import Chip, FPGA
from siliconcompiler.scheduler import _setup_node
from siliconcompiler.targets import fpgaflow_demo
from siliconcompiler.flows import fpgaflow
from siliconcompiler.tools.vpr import route, place
from siliconcompiler.flowgraph import _get_flowgraph_execution_order


@pytest.fixture
def designs_dir(datadir):
    return os.path.join(datadir, 'fpga_designs')


@pytest.fixture
def sample_fpgas(examples_root):
    flow_root = os.path.join(examples_root, 'fpga_flow')

    fpgas = {}

    # Settings common to all parts in family
    for part_name in (
            'example_arch_X005Y005',
            'example_arch_X008Y008',
            'example_arch_X014Y014',
            'example_arch_X030Y030'):
        fpga = FPGA(part_name)

        fpga.set('fpga', part_name, 'vendor', 'N/A')

        # Part name is specified per architecture file.  Device code specifies
        # which <fixed_layout> name to use when running VPR.  These examples
        # use the following names:
        if (part_name == 'example_arch_X005Y005'):
            fpga.set('fpga', part_name, 'var', 'vpr_device_code', 'fpga_beta')
        else:
            fpga.set('fpga', part_name, 'var', 'vpr_device_code', part_name)

        fpga.set('fpga', part_name, 'lutsize', 4)

        arch_root = os.path.join(flow_root, 'arch', part_name)
        fpga.set('fpga', part_name, 'file', 'archfile', os.path.join(arch_root, f'{part_name}.xml'))

        fpga.set('fpga', part_name, 'var', 'vpr_clock_model', 'ideal')

        if (part_name == 'example_arch_X005Y005'):
            arch_root = os.path.join(flow_root, 'arch', part_name)
            fpga.set('fpga', part_name, 'file', 'graphfile',
                     os.path.join(arch_root, 'example_arch_X005Y005_rr_graph.xml'))
            fpga.set('fpga', part_name, 'var', 'channelwidth', 32)

        if (part_name == 'example_arch_X008Y008'):
            # No RR graph for this architecture to support testing
            fpga.set('fpga', part_name, 'var', 'channelwidth', 32)

        if ((part_name == 'example_arch_X014Y014') or (part_name == 'example_arch_X030Y030')):

            techlib_root = os.path.join(flow_root, 'techlib')

            if (part_name == 'example_arch_X014Y014'):
                fpga.set('fpga', part_name, 'file', 'constraints_map',
                         os.path.join(arch_root, f'{part_name}_constraint_map.json'))

            fpga.set('fpga', part_name, 'var', 'channelwidth', 80)
            fpga.add('fpga', part_name, 'var', 'feature_set', 'async_set')
            fpga.add('fpga', part_name, 'var', 'feature_set', 'async_reset')
            fpga.add('fpga', part_name, 'var', 'feature_set', 'enable')
            fpga.add('fpga', part_name, 'file', 'yosys_flop_techmap',
                     os.path.join(techlib_root, 'example_arch_techmap_flops.v'))

            fpga.add('fpga', part_name, 'file', 'yosys_dsp_techmap',
                     os.path.join(techlib_root, 'example_arch_techmap_dsp.v'))

            fpga.add('fpga', part_name, 'file', 'yosys_extractlib',
                     os.path.join(techlib_root, 'example_arch_techmap_dsp_extract.v'))

            # The same library used for the extraction pass can also be used to
            # define macros that can be passed through synthesis, specify that here
            fpga.add('fpga', part_name, 'file', 'yosys_macrolib',
                     os.path.join(techlib_root, 'example_arch_techmap_dsp_extract.v'))

            fpga.add('fpga', part_name, 'var', 'yosys_dsp_options', 'DSP_A_MAXWIDTH=18')
            fpga.add('fpga', part_name, 'var', 'yosys_dsp_options', 'DSP_B_MAXWIDTH=18')
            fpga.add('fpga', part_name, 'var', 'yosys_dsp_options', 'DSP_A_MINWIDTH=2')
            fpga.add('fpga', part_name, 'var', 'yosys_dsp_options', 'DSP_B_MINWIDTH=2')
            fpga.add('fpga', part_name, 'var', 'yosys_dsp_options', 'DSP_NAME=_dsp_block_')

            fpga.add('fpga', part_name, 'file', 'yosys_memory_techmap',
                     os.path.join(techlib_root, 'example_arch_techmap_bram.v'))
            fpga.add('fpga', part_name, 'file', 'yosys_memory_libmap',
                     os.path.join(techlib_root, 'example_arch_bram_memory_map.txt'))

        fpgas[part_name] = fpga

    return fpgas


@pytest.mark.eda
@pytest.mark.quick
def test_fpgaflow(sample_fpgas, designs_dir):
    chip = Chip("adder")

    # 1. Defining the project
    chip.set('fpga', 'partname', 'example_arch_X005Y005')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "adder.v"))

    # 3. Load target
    chip.use(fpgaflow_demo)
    chip.use(sample_fpgas[chip.get('fpga', 'partname')])

    assert chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


@pytest.mark.eda
@pytest.mark.quick
def test_fpgaflow_apr(sample_fpgas, designs_dir):
    chip = Chip("adder")

    # 1. Defining the project
    chip.set('fpga', 'partname', 'example_arch_X008Y008')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "adder.v"))

    # 3. Load target
    chip.use(fpgaflow_demo)
    chip.use(sample_fpgas[chip.get('fpga', 'partname')])

    chip.set('option', 'to', 'route')

    assert chip.run()

    route_file = chip.find_result('route', step='route')

    assert os.path.exists(route_file)


@pytest.mark.eda
@pytest.mark.quick
def test_fpgaflow_screenshot(sample_fpgas, designs_dir):
    chip = Chip("adder")

    # 1. Defining the project
    chip.set('fpga', 'partname', 'example_arch_X005Y005')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "adder.v"))

    # 3. Load target
    chip.use(fpgaflow_demo)
    chip.use(sample_fpgas[chip.get('fpga', 'partname')])

    assert chip.run()

    route_file = chip.find_result('route', step='route')

    screenshot_path = chip.show(route_file, screenshot=True)
    assert screenshot_path
    assert os.path.exists(screenshot_path)


@pytest.mark.eda
@pytest.mark.quick
def test_flopmap_fpgaflow(sample_fpgas, designs_dir):
    chip = Chip("updowncount")

    # 1. Defining the project
    chip.set('fpga', 'partname', 'example_arch_X014Y014')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "updowncount.v"))

    # 3. Load target
    chip.use(fpgaflow_demo)
    chip.use(sample_fpgas[chip.get('fpga', 'partname')])

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
def test_dspmap_fpgaflow(sample_fpgas, designs_dir):
    chip = Chip('macc_pipe')

    # 1. Defining the project
    chip.set('fpga', 'partname', 'example_arch_X014Y014')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "macc_pipe.v"))

    # 3. Load target
    chip.use(fpgaflow_demo)
    chip.use(sample_fpgas[chip.get('fpga', 'partname')])

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
def test_dspextract_fpgaflow(sample_fpgas, designs_dir):
    chip = Chip('macc_pipe')

    # 1. Defining the project
    chip.set('fpga', 'partname', 'example_arch_X030Y030')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "macc_pipe.v"))

    # 3. Load target
    chip.use(fpgaflow_demo)
    chip.use(sample_fpgas[chip.get('fpga', 'partname')])

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
def test_dspblackbox_fpgaflow(sample_fpgas, designs_dir):
    chip = Chip('macc')

    # 1. Defining the project
    chip.set('fpga', 'partname', 'example_arch_X030Y030')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "macc.v"))

    # 3. Load target
    chip.use(fpgaflow_demo)
    chip.use(sample_fpgas[chip.get('fpga', 'partname')])

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
def test_matrix_multiply_fpgaflow(sample_fpgas, designs_dir):

    chip = Chip('matrix_multiply')

    # 1. Defining the project
    chip.set('fpga', 'partname', 'example_arch_X030Y030')

    # 2. Define source files
    for src in (os.path.join(designs_dir, 'matrix_multiply', 'matrix_multiply.v'),
                os.path.join(designs_dir, 'matrix_multiply', 'matrix_multiply_control.v'),
                os.path.join(designs_dir, 'matrix_multiply', 'row_col_data_mux.v'),
                os.path.join(designs_dir, 'matrix_multiply', 'row_col_memory.v'),
                os.path.join(designs_dir, 'matrix_multiply', 'row_col_multiply.v'),
                os.path.join(designs_dir, 'matrix_multiply', 'row_col_product_adder.v')):
        chip.input(src)

    # 3. Load target
    chip.use(fpgaflow_demo)
    chip.use(sample_fpgas[chip.get('fpga', 'partname')])

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
def test_mem_to_flops_fpgaflow(sample_fpgas, designs_dir):
    chip = Chip('register_file')

    # 1. Defining the project
    chip.set('fpga', 'partname', 'example_arch_X030Y030')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "register_file.v"))

    # 3. Load target
    chip.use(fpgaflow_demo)
    chip.use(sample_fpgas[chip.get('fpga', 'partname')])

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
def test_fpgaflow_vhdl(sample_fpgas, designs_dir):
    chip = Chip('adder')

    # 1. Defining the project
    chip.set('fpga', 'partname', 'example_arch_X005Y005')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "adder.vhd"))

    # 3. Load target
    chip.use(fpgaflow_demo)
    chip.use(sample_fpgas[chip.get('fpga', 'partname')])

    assert chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


@pytest.mark.eda
@pytest.mark.quick
def test_fpga_constraints(sample_fpgas, designs_dir):
    chip = Chip('adder')

    # 1. Defining the project
    chip.set('fpga', 'partname', 'example_arch_X005Y005')

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

    # 4. Load target
    chip.use(fpgaflow_demo)
    chip.use(sample_fpgas[chip.get('fpga', 'partname')])

    assert chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


@pytest.mark.eda
@pytest.mark.quick
def test_fpga_pcf_constraints(sample_fpgas, designs_dir):
    chip = Chip('adder')

    # 1. Defining the project
    chip.set('fpga', 'partname', 'example_arch_X014Y014')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "adder.v"))

    # 3. Set placement constraints
    chip.input(os.path.join(designs_dir, "adder_pin_constraints_example_arch_X014Y014.pcf"))

    # 4. Load target
    chip.use(fpgaflow_demo)
    chip.use(sample_fpgas[chip.get('fpga', 'partname')])

    assert chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


@pytest.mark.eda
@pytest.mark.quick
def test_fpga_xml_constraints(sample_fpgas, designs_dir, datadir):
    chip = Chip('adder')

    # 1. Defining the project
    chip.set('fpga', 'partname', 'example_arch_X014Y014')

    # 2. Define source files
    chip.input(os.path.join(designs_dir, "adder.v"))

    # 3. Set placement constraints
    chip.add('input', 'constraint', 'vpr_pins',
             os.path.join(datadir, 'test_fpgaflow', 'pin_constraints_example_arch_X014Y014.xml'))

    # 4. Load target
    chip.use(fpgaflow_demo)
    chip.use(sample_fpgas[chip.get('fpga', 'partname')])

    assert chip.run()

    fasm_file = chip.find_result('fasm', step='bitstream')

    assert os.path.exists(fasm_file)


def test_vpr_max_router_iterations(sample_fpgas):
    chip = Chip('foo')
    chip.input('test.v')

    chip.set('fpga', 'partname', 'example_arch_X008Y008')

    chip.set('tool', 'vpr', 'task', 'route', 'var', 'max_router_iterations', 300)

    # 3. Load target
    chip.use(fpgaflow_demo)
    chip.use(sample_fpgas[chip.get('fpga', 'partname')])

    # Verify that the user's setting doesn't get clobbered
    # by the FPGA flow
    for layer_nodes in _get_flowgraph_execution_order(chip, 'fpgaflow'):
        for step, index in layer_nodes:
            _setup_node(chip, step, index)

    assert '300' == \
        chip.get('tool', 'vpr', 'task', 'route', 'var', 'max_router_iterations',
                 step='route', index='0')[0]

    chip.set('arg', 'step', 'route')
    chip.set('arg', 'index', '0')
    assert '--max_router_iterations 300' in route.runtime_options(chip)


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
