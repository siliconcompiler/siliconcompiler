import os
import shutil

from siliconcompiler.tools.vpr import vpr


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
             step=step, index=index, clobber=clobber)

    # TO-DO: PRIOROTIZE the post-routing packing results?
    design = chip.top()
    chip.set('tool', tool, 'task', task, 'input', design + '.blif', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'input', design + '.net', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'input', design + '.place', step=step, index=index)

    chip.set('tool', tool, 'task', task, 'output', design + '.route', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.blif', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.net', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.place', step=step, index=index)


def runtime_options(chip):
    '''Command line options to vpr for the route step
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    design = chip.top()

    options = vpr.runtime_options(chip)

    blif = f"inputs/{design}.blif"
    options.append(blif)

    options.append('--route')
    # To run only the routing step we need to pass in the placement files
    options.append(f'--net_file inputs/{design}.net')
    options.append(f'--place_file inputs/{design}.place')

    enable_images = chip.get('tool', tool, 'task', task, 'var', 'enable_images',
                             step=step, index=index)[0]

    if enable_images == 'true':
        design = chip.top()

        graphics_commands = vpr.get_common_graphics(chip)

        # set_draw_block_text 0 hides the label for various blocks in the design
        # set_draw_block_outlines 0 removes the outline/boundary for various blocks in the design
        # set_routing_util 1 displays the routing utilization as a heat map
        # set_routing_util 4 displays the routing utilization as a heat map over placed blocks
        # Refer: https://github.com/verilog-to-routing/vtr-verilog-to-routing/blob/master/
        # vpr/src/draw/draw_types.h#L89
        # save_graphics saves the block diagram as a png/svg/pdf
        # Refer:
        # https://docs.verilogtorouting.org/en/latest/vpr/command_line_usage/#graphics-options
        graphics_commands.append("set_draw_block_text 0; " +
                                 "set_draw_block_outlines 0; " +
                                 "set_routing_util 1; " +
                                 "save_graphics "
                                 f"reports/{design}_route_utilization_with_placement.png;")
        graphics_commands.append("set_draw_block_text 0; " +
                                 "set_draw_block_outlines 0; " +
                                 "set_routing_util 4; " +
                                 "save_graphics "
                                 f"reports/{design}_route_utilization.png;")

        graphics_command_str = " ".join(graphics_commands)

        options.append("--graphics_commands")
        options.append(f"\"{graphics_command_str}\"")

    return options


################################
# Post_process (post executable)
################################


def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    vpr.vpr_post_process(chip)

    design = chip.top()
    # Forward all of the prior step inputs forward for bitstream generation
    shutil.copy(f'inputs/{design}.blif', 'outputs')
    shutil.copy(f'inputs/{design}.net', 'outputs')
    shutil.copy(f'inputs/{design}.place', 'outputs')
