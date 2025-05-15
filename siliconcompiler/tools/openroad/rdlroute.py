import os

from siliconcompiler import utils
from siliconcompiler.tools._common import input_provides, get_tool_task
from siliconcompiler.tools._common.asic import set_tool_task_var
from siliconcompiler.tools.openroad._apr import build_pex_corners
from siliconcompiler.tools.openroad._apr import extract_metrics


def setup(chip):
    '''
    Perform floorplanning, pin placements, macro placements and power grid generation
    '''

    # Generic tool setup.
    # default tool settings, note, not additive!

    tool = 'openroad'
    script = 'sc_rdlroute.tcl'
    refdir = os.path.join('tools', tool, 'scripts')

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    design = chip.top()

    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vswitch', '-version')
    chip.set('tool', tool, 'version', '>=v2.0-17581')
    chip.set('tool', tool, 'format', 'tcl')

    # exit automatically in batch mode and not breakpoint
    option = ['-no_init']
    if exit and not chip.get('option', 'breakpoint', step=step, index=index):
        option.append("-exit")

    option.extend(["-metrics", "reports/metrics.json"])
    chip.set('tool', tool, 'task', task, 'option', option, step=step, index=index)

    # Input/Output requirements for default asicflow steps

    chip.set('tool', tool, 'task', task, 'refdir', refdir,
             step=step, index=index,
             package='siliconcompiler')
    chip.set('tool', tool, 'task', task, 'script', script,
             step=step, index=index)
    chip.set('tool', tool, 'task', task, 'threads', utils.get_cores(chip),
             step=step, index=index, clobber=False)

    if chip.get('option', 'nodisplay'):
        # Tells QT to use the offscreen platform if nodisplay is used
        chip.set('tool', tool, 'task', task, 'env', 'QT_QPA_PLATFORM', 'offscreen',
                 step=step, index=index)

    # basic warning and error grep check on logfile
    chip.set('tool', tool, 'task', task, 'regex', 'warnings', r'^\[WARNING|^Warning',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'errors', r'^\[ERROR',
             step=step, index=index, clobber=False)

    chip.add('tool', tool, 'task', task, 'require',
             'option,var,openroad_libtype',
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'require',
             ','.join(['tool', tool, 'task', task, 'file', 'rdlroute']),
             step=step, index=index)
    chip.set('tool', tool, 'task', task, 'file', 'rdlroute',
             'script to perform rdl route',
             field='help')

    set_tool_task_var(chip, param_key='fin_add_fill',
                      default_value='false',
                      schelp='true/false, when true enables adding fill, '
                             'if enabled by the PDK, to the design',
                      skip='lib')

    chip.set('tool', tool, 'task', task, 'var', 'debug_level',
             'list of "tool key level" to enable debugging of OpenROAD',
             field='help')

    if f'{design}.v' in input_provides(chip, step, index):
        chip.add('tool', tool, 'task', task, 'input', design + '.v', step=step, index=index)
    elif f'{design}.vg' in input_provides(chip, step, index):
        chip.add('tool', tool, 'task', task, 'input', design + '.vg', step=step, index=index)
    else:
        chip.add('tool', tool, 'task', task, 'require',
                 ','.join(['input', 'netlist', 'verilog']),
                 step=step, index=index)

    chip.add('tool', tool, 'task', task, 'output', design + '.vg', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.def', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.odb', step=step, index=index)


def pre_process(chip):
    build_pex_corners(chip)


def post_process(chip):
    extract_metrics(chip)
