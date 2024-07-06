import os
import shutil
from siliconcompiler import SiliconCompilerError
from siliconcompiler.tools.vpr import vpr
from siliconcompiler.tools.vpr._json_constraint import load_constraints_map
from siliconcompiler.tools.vpr._json_constraint import load_json_constraints
from siliconcompiler.tools.vpr._json_constraint import map_constraints
from siliconcompiler.tools.vpr._xml_constraint import generate_vpr_constraints_xml_file
from siliconcompiler.tools._common import get_tool_task


def setup(chip, clobber=True):
    '''
    Perform automated place and route with VPR
    '''

    tool = 'vpr'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    vpr.setup_tool(chip, clobber=clobber)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    design = chip.top()
    chip.set('tool', tool, 'task', task, 'input', design + '.blif', step=step, index=index)

    chip.set('tool', tool, 'task', task, 'output', design + '.blif', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.net', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.place', step=step, index=index)


def runtime_options(chip):
    '''Command line options to vpr for the place step
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    design = chip.top()

    options = vpr.runtime_options(chip)

    blif = f"inputs/{design}.blif"
    options.append(blif)

    options.append('--pack')
    options.append('--place')

    enable_images = chip.get('tool', tool, 'task', task, 'var', 'enable_images',
                             step=step, index=index)[0]

    if enable_images == 'true':
        graphics_commands = vpr.get_common_graphics(chip)

        graphics_command_str = " ".join(graphics_commands)

        options.append("--graphics_commands")
        options.append(f"\"{graphics_command_str}\"")

    return options


################################
# Pre_process (pre executable)
################################


def pre_process(chip):
    ''' Tool specific function to run before step execution
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    part_name = chip.get('fpga', 'partname')

    # If the user explicitly provides an XML constraints file, give that
    # priority over other constraints input types:
    if 'vpr_pins' in chip.getkeys('input', 'constraint'):
        constraint_file = vpr.find_single_file(chip, 'input', 'constraint', 'vpr_pins',
                                               step=step, index=index,
                                               file_not_found_msg="VPR constraints file not found")

        if (constraint_file is not None):
            shutil.copy2(constraint_file, vpr.auto_constraints())

    elif 'pcf' in chip.getkeys('input', 'constraint'):
        constraint_file = vpr.find_single_file(chip, 'input', 'constraint', 'pcf',
                                               step=step, index=index,
                                               file_not_found_msg="PCF constraints file not found")

        map_file = vpr.find_single_file(chip, 'fpga', part_name, 'file', 'constraints_map',
                                        file_not_found_msg="constraints map not found")

        if not map_file:
            raise SiliconCompilerError('FPGA does not have required constraints map', chip=chip)

        constraints_map = load_constraints_map(map_file)
        json_constraints = load_json_constraints(constraint_file)
        all_place_constraints, missing_pins = map_constraints(chip,
                                                              json_constraints,
                                                              constraints_map)
        if (missing_pins > 0):
            raise SiliconCompilerError(
                "Pin constraints specify I/O ports not in this architecture", chip=chip)

        generate_vpr_constraints_xml_file(all_place_constraints, vpr.auto_constraints())

    else:
        all_component_constraints = chip.getkeys('constraint', 'component')
        all_place_constraints = {}
        for component in all_component_constraints:
            place_constraint = chip.get('constraint', 'component', component, 'placement',
                                        step=step, index=index)
            chip.logger.info(f'Place constraint for {component} at {place_constraint}')
            all_place_constraints[component] = place_constraint

        if all_place_constraints:
            generate_vpr_constraints_xml_file(all_place_constraints, vpr.auto_constraints())


################################
# Post_process (post executable)
################################


def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    vpr.vpr_post_process(chip)

    design = chip.top()
    shutil.copy2(f'inputs/{design}.blif', 'outputs')
