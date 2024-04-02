import os

from siliconcompiler.tools.vpr import vpr


def setup(chip, clobber=True):
    '''
    Show placed and/or routed designs in VPR GUI
    '''

    tool = 'vpr'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    vpr.setup_tool(chip, clobber=clobber)

    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)


def runtime_options(chip):
    '''Command line options to vpr for show
    '''

    options = generic_show_options(chip)

    options.append('--disp on')

    return options


def generic_show_options(chip):
    ''' Helper function to setup options for show and screenshot
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    options = vpr.runtime_options(chip)

    if chip.valid('tool', tool, 'task', task, 'var', 'show_filepath'):
        show_job = chip.get('tool', tool, 'task', task, 'var', 'show_job',
                            step=step, index=index)
        show_step = chip.get('tool', tool, 'task', task, 'var', 'show_step',
                             step=step, index=index)

        blif_file = chip.find_result('blif', show_step[0],
                                     jobname=show_job[0])
        net_file = chip.find_result('net', show_step[0],
                                    jobname=show_job[0])
        place_file = chip.find_result('place', show_step[0],
                                      jobname=show_job[0])
        route_file = chip.find_result('route', show_step[0],
                                      jobname=show_job[0])

    if blif_file:
        options.append(f'{blif_file}')
    else:
        chip.error("Blif file does not exist", fatal=True)

    if net_file:
        options.append(f'--net_file {net_file}')
    else:
        chip.error("Net file does not exist", fatal=True)

    if route_file and place_file:
        options.append('--analysis')
        options.append(f'--place_file {place_file}')
        options.append(f'--route_file {route_file}')
    elif place_file:
        options.append('--route')
        options.append('--max_router_iterations 0')
        options.append(f'--place_file {place_file}')
    else:
        chip.error("Place file does not exist", fatal=True)

    return options
