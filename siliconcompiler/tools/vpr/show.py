import os
from siliconcompiler import utils
from siliconcompiler import SiliconCompilerError
from siliconcompiler.tools.vpr import vpr
from siliconcompiler.tools._common import get_tool_task


def setup(chip, clobber=True):
    '''
    Show placed and/or routed designs in VPR GUI
    '''

    tool = 'vpr'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    vpr.setup_tool(chip, clobber=clobber)

    chip.set('tool', tool, 'task', task, 'threads', utils.get_cores(chip),
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

    design = chip.top()

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    options = vpr.runtime_options(chip)

    file_path = chip.get('tool', tool, 'task', task, 'var', 'show_filepath',
                         step=step, index=index)
    if not file_path:
        raise SiliconCompilerError("Please provide a place or route file", chip=chip)

    if os.path.exists(file_path[0]):
        file_dir = os.path.dirname(file_path[0])
        blif_file = os.path.join(file_dir, f'{design}.blif')
        net_file = os.path.join(file_dir, f'{design}.net')
        place_file = os.path.join(file_dir, f'{design}.place')
        route_file = os.path.join(file_dir, f'{design}.route')
    else:
        raise SiliconCompilerError("Invalid filepath", chip=chip)

    if os.path.exists(blif_file):
        options.append(blif_file)
    else:
        raise SiliconCompilerError("Blif file does not exist", chip=chip)

    if os.path.exists(net_file):
        options.extend(['--net_file', net_file])
    else:
        raise SiliconCompilerError("Net file does not exist", chip=chip)

    if os.path.exists(route_file) and os.path.exists(place_file):
        options.append('--analysis')
        options.extend(['--place_file', place_file])
        options.extend(['--route_file', route_file])
    elif os.path.exists(place_file):
        # NOTE: This is a workaround to display the VPR GUI on the output of the place step.
        # VPR GUI can be invoked during the place, route or analysis steps - not after they are run.
        # Analysis can only be run after route. Hence, the only way to display the output
        # of the is to run the route step. Performing routing could take a significant amount
        # of time, which would not be useful if the user is simply looking to visualize
        # the placed design. Setting max_router_iterations to 0 avoids running routing iterations
        # and provides a fast way to invoke VPR GUI on the placed design.
        options.append('--route')
        options.extend(['--max_router_iterations', 0])
        options.extend(['--place_file', place_file])
    else:
        raise SiliconCompilerError("Place file does not exist", chip=chip)

    return options
