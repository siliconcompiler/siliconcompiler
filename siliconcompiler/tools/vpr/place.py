import os
import shutil

from siliconcompiler.tools.vpr import vpr
from siliconcompiler.tools.vpr.xml_constraints_gen import generate_vpr_constraints_xml
from siliconcompiler.tools.vpr.xml_constraints_gen import write_vpr_constraints_xml_file


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

    design = chip.top()

    if 'pins' in chip.getkeys('input', 'constraint'):
        chip.logger.info("Using pin constraints file instead of pin constraints from chip.set")
    else:
        all_component_constraints = chip.getkeys('constraint', 'component')
        all_place_constraints = {}
        if (len(all_component_constraints) > 0):
            for component in all_component_constraints:
                place_constraint = chip.get('constraint', 'component', component, 'placement')
                chip.logger.info(f'Place constraint for {component} at {place_constraint}')
                all_place_constraints[component] = place_constraint

            constraints_xml = generate_vpr_constraints_xml(all_place_constraints)
            xml_file = f'inputs/{design}_constraints.xml'
            write_vpr_constraints_xml_file(constraints_xml, xml_file)

    # TODO: return error code
    return 0


################################
# Post_process (post executable)
################################


def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    for file in chip.get('tool', 'vpr', 'task', task, 'output', step=step, index=index):
        shutil.copy(file, 'outputs')
    design = chip.top()
    shutil.copy(f'inputs/{design}.blif', 'outputs')
    # TODO: return error code
    return 0
