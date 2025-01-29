import os
import re
import shutil
from siliconcompiler.utils import sc_open
from siliconcompiler.tools._common.asic import set_tool_task_var, set_tool_task_lib_var, get_mainlib
from siliconcompiler.tools._common.asic_clock import get_clock_period, add_clock_requirements
from siliconcompiler.tools._common import \
    add_frontend_requires, add_require_input, get_frontend_options, get_input_files, \
    get_tool_task, has_input_files, record_metric


def make_docs(chip):
    from siliconcompiler.targets import freepdk45_demo
    chip.use(freepdk45_demo)
    chip.input('<design>.c')
    return setup(chip)


def setup(chip):
    '''
    Performs high level synthesis to generate a verilog output
    '''

    if not has_input_files(chip, 'input', 'hll', 'c') and \
       not has_input_files(chip, 'input', 'hll', 'llvm'):
        return "no files in [input,hll,c] or [input,hll,llvm]"

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    # Standard Setup
    refdir = 'tools/' + tool
    chip.set('tool', tool, 'exe', 'bambu')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=2024.03', clobber=False)

    chip.set('tool', tool, 'task', task, 'refdir', refdir,
             step=step, index=index,
             package='siliconcompiler', clobber=False)

    # Input/Output requirements
    chip.add('tool', tool, 'task', task, 'output', chip.top() + '.v', step=step, index=index)

    add_clock_requirements(chip)

    # Schema requirements
    add_require_input(chip, 'input', 'hll', 'c')
    add_require_input(chip, 'input', 'hll', 'llvm')
    add_frontend_requires(chip, ['idir', 'define'])

    set_tool_task_var(chip, 'device',
                      schelp="Device to use during bambu synthesis")
    set_tool_task_lib_var(chip, 'memorychannels', default_value=1,
                          schelp="Number of memory channels available")

    # Require clock conversion factor, from library units to ns
    mainlib = get_mainlib(chip)
    chip.add('tool', tool, 'task', task, 'require',
             ','.join(['library', mainlib, 'option', 'var', 'bambu_clock_multiplier']),
             step=step, index=index)

    set_tool_task_var(chip, 'clock_multiplier',
                      schelp="Clock multiplier used to convert library units to ns")


################################
#  Custom runtime options
################################
def runtime_options(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    cmdlist = []

    opts = get_frontend_options(chip, ['idir', 'define'])

    for value in opts['idir']:
        cmdlist.append('-I' + value)
    for value in opts['define']:
        cmdlist.append('-D' + value)
    for value in get_input_files(chip, 'input', 'hll', 'c'):
        cmdlist.append(value)
    if not has_input_files(chip, 'input', 'hll', 'c'):
        # Only use llvm if C is empty
        for value in get_input_files(chip, 'input', 'hll', 'llvm'):
            cmdlist.append(value)

    cmdlist.append('--soft-float')
    cmdlist.append('--memory-allocation-policy=NO_BRAM')

    mem_channels = int(chip.get('tool', tool, 'task', task, 'var', 'memorychannels',
                                step=step, index=index)[0])
    if mem_channels > 0:
        cmdlist.append(f'--channels-number={mem_channels}')

    mainlib = get_mainlib(chip)
    clock_multiplier = float(chip.get('library', mainlib, 'option', 'var',
                                      'bambu_clock_multiplier')[0])
    clock_name, period = get_clock_period(chip, clock_units_multiplier=clock_multiplier)
    if clock_name:
        cmdlist.append(f'--clock-name={clock_name}')
    if period:
        cmdlist.append(f'--clock-period={period}')

    cmdlist.append('--disable-function-proxy')

    device = chip.get('tool', tool, 'task', task, 'var', 'device',
                      step=step, index=index)
    if device:
        cmdlist.append(f'--device={device[0]}')

    cmdlist.append(f'--top-fname={chip.top(step, index)}')

    return cmdlist


################################
# Post_process (post executable)
################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    shutil.copy2(f'{chip.top(step, index)}.v', os.path.join('outputs', f'{chip.top()}.v'))

    ff = re.compile(fr"Total number of flip-flops in function {chip.top(step, index)}: (\d+)")
    area = re.compile(r"Total estimated area: (\d+)")
    fmax = re.compile(r"Estimated max frequency \(MHz\): (\d+\.?\d*)")
    slack = re.compile(r"Minimum slack: (\d+\.?\d*)")

    log_file = f"{step}.log"
    with sc_open(log_file) as log:
        for line in log:
            ff_match = ff.findall(line)
            area_match = area.findall(line)
            fmax_match = fmax.findall(line)
            slack_match = slack.findall(line)
            if ff_match:
                record_metric(chip, step, index, "registers", int(ff_match[0]), log_file)
            if area_match:
                record_metric(chip, step, index, "cellarea", float(area_match[0]), log_file,
                              source_unit='um^2')
            if fmax_match:
                record_metric(chip, step, index, "fmax", float(fmax_match[0]), log_file,
                              source_unit='MHz')
            if slack_match:
                slack_ns = float(slack_match[0])
                if slack_ns >= 0:
                    record_metric(chip, step, index, "setupwns", 0, log_file,
                                  source_unit='ns')
                else:
                    record_metric(chip, step, index, "setupwns", slack_ns, log_file,
                                  source_unit='ns')
                record_metric(chip, step, index, "setupslack", slack_ns, log_file,
                              source_unit='ns')
