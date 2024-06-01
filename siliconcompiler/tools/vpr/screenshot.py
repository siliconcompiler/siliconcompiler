from siliconcompiler.tools.vpr import show


def setup(chip, clobber=True):
    '''
    Screenshot placed and/or routed designs
    '''

    show.setup(chip, clobber=clobber)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    design = chip.top()
    chip.add('tool', tool, 'task', task, 'output', f'{design}.png', step=step, index=index)


def runtime_options(chip):
    '''Command line options to vpr for screenshot
    '''

    design = chip.top()

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    if chip.valid('tool', tool, 'task', task, 'var', 'show_filepath'):
        show_type = chip.get('tool', tool, 'task', task, 'var', 'show_filetype',
                             step=step, index=index)[0]
    else:
        chip.error("Invalid filepath", fatal=True)

    options = show.generic_show_options(chip)

    if show_type == 'route':
        screenshot_command_str = ("set_draw_block_text 0; " +
                                  "set_draw_block_outlines 0; " +
                                  "set_routing_util 1; " +
                                  f"save_graphics outputs/{design}.png;")
    elif show_type == 'place':
        screenshot_command_str = ("set_draw_block_text 1; " +
                                  "set_draw_block_outlines 1; " +
                                  f"save_graphics outputs/{design}.png;")
    else:
        chip.error(f"Incorrect file type {show_type}", fatal=True)

    options.append("--graphics_commands")
    options.append(f"\"{screenshot_command_str}\"")

    return options
