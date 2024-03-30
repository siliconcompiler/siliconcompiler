import os
import shutil

from siliconcompiler.tools.vpr import vpr
from siliconcompiler.tools.vpr._json_constraint import load_constraints_map
from siliconcompiler.tools.vpr._json_constraint import load_json_constraints
from siliconcompiler.tools.vpr._json_constraint import map_constraints
from siliconcompiler.tools.vpr._xml_constraint import generate_vpr_constraints_xml
from siliconcompiler.tools.vpr._xml_constraint import write_vpr_constraints_xml_file


def setup(chip, clobber=True):
    '''
    Perform automated place and route with VPR
    '''

    tool = 'vpr'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    vpr.setup_tool(chip, clobber=clobber)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    design = chip.top()
    chip.set('tool', tool, 'task', task, 'output', design + '.net', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.place', step=step, index=index)


################################
# Pre_process (pre executable)
################################


def pre_process(chip):
    ''' Tool specific function to run before step execution
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    part_name = chip.get('fpga', 'partname')

    if 'pinmap' in chip.getkeys('input', 'constraint'):

        constraint_file = vpr.find_single_file(chip, 'input', 'constraint', 'pinmap',
                                               step=step, index=index,
                                               file_not_found_msg="JSON constraints file not found")

        map_file = vpr.find_single_file(chip, 'fpga', part_name, 'file', 'constraints_map',
                                        file_not_found_msg="constraints map not found")

        constraints_map = load_constraints_map(map_file)
        json_constraints = load_json_constraints(constraint_file)
        all_place_constraints = map_constraints(json_constraints, constraints_map)

        constraints_xml = generate_vpr_constraints_xml(all_place_constraints)
        write_vpr_constraints_xml_file(constraints_xml, vpr.auto_constraints())

    elif not chip.valid('input', 'constraint', 'pins', default_valid=True):
        all_component_constraints = chip.getkeys('constraint', 'component')
        all_place_constraints = {}
        for component in all_component_constraints:
            place_constraint = chip.get('constraint', 'component', component, 'placement',
                                        step=step, index=index)
            chip.logger.info(f'Place constraint for {component} at {place_constraint}')
            all_place_constraints[component] = place_constraint

        constraints_xml = generate_vpr_constraints_xml(all_place_constraints)
        write_vpr_constraints_xml_file(constraints_xml, vpr.auto_constraints())

    # TODO: return error code
    return 0


################################
# Post_process (post executable)
################################


def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    vpr.vpr_post_process(chip)

    design = chip.top()
    shutil.copy(f'inputs/{design}.blif', 'outputs')
