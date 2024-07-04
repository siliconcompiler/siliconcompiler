'''
Surelog is a SystemVerilog pre-processor, parser, elaborator,
and UHDM compiler that provides IEEE design and testbench
C/C++ VPI and a Python AST API.

Documentation: https://github.com/chipsalliance/Surelog

Sources: https://github.com/chipsalliance/Surelog

Installation: https://github.com/chipsalliance/Surelog
'''

import os
import sys
import shutil
from siliconcompiler.tools._common import get_tool_task


################################
# Setup Tool (pre executable)
################################
def setup(chip):
    ''' Sets up default settings common to running Surelog.
    '''

    tool = 'surelog'
    # Nothing in this method should rely on the value of 'step' or 'index', but they are used
    # as schema keys in some important places, so we still need to fetch them.
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    exe = tool
    _, task = get_tool_task(chip, step, index)

    is_docker = chip.get('option', 'scheduler', 'name', step=step, index=index) == 'docker'
    # Although Windows will find the binary even if the .exe suffix is omitted,
    # Surelog won't find the relative builtin.sv file unless we add it.
    if sys.platform.startswith('win32') and not is_docker:
        exe = f'{tool}.exe'

    # Standard Setup
    chip.set('tool', tool, 'exe', exe)
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=1.51', clobber=False)

    # We package SC wheels with a precompiled copy of Surelog installed to
    # tools/surelog/bin. If the user doesn't have Surelog installed on their
    # system path, set the path to the bundled copy in the schema.
    if shutil.which(exe) is None and not is_docker:
        surelog_path = os.path.join(os.path.dirname(__file__), 'bin')
        if os.path.exists(os.path.join(surelog_path, exe)):
            chip.set('tool', tool, 'path', surelog_path, clobber=False)

    # Log file parsing
    chip.set('tool', tool, 'task', task, 'regex', 'warnings', r'^\[WRN:',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'errors', r'^\[(ERR|FTL|SNT):',
             step=step, index=index, clobber=False)

    for warning in chip.get('tool', tool, 'task', task, 'warningoff', step=step, index=index):
        chip.add('tool', tool, 'regex', step, index, 'warnings', f'-v {warning}',
                 step=step, index=index)

    chip.set('tool', tool, 'task', task, 'var', 'enable_lowmem',
             'true/false, when true instructs Surelog to minimize its maximum memory usage.',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'enable_lowmem', 'false',
             step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'var', 'disable_write_cache',
             'true/false, when true instructs Surelog to not write to its cache.',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'disable_write_cache', 'false',
             step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'var', 'disable_info',
             'true/false, when true instructs Surelog to not log infos.',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'disable_info', 'false',
             step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'var', 'disable_note',
             'true/false, when true instructs Surelog to not log notes.',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'disable_note', 'false',
             step=step, index=index, clobber=False)


def parse_version(stdout):
    # Surelog --version output looks like:
    # VERSION: 1.13
    # BUILT  : Nov 10 2021

    # grab version # by splitting on whitespace
    return stdout.split()[1]


def runtime_options(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    # Command-line options.
    options = []

    # With newer versions of Surelog (at least 1.35 and up), this option is
    # necessary to make bundled versions work.
    # TODO: why?
    options.append('-nocache')

    lowmem = chip.get('tool', tool, 'task', task, 'var', 'enable_lowmem', step=step, index=index)
    if lowmem == ['true']:
        options.append('-lowmem')

    no_write_cache = chip.get('tool', tool, 'task', task, 'var', 'disable_write_cache', step=step,
                              index=index)
    if no_write_cache == ['true']:
        options.append('-nowritecache')

    no_info = chip.get('tool', tool, 'task', task, 'var', 'disable_info', step=step, index=index)
    if no_info == ['true']:
        options.append('-noinfo')

    no_note = chip.get('tool', tool, 'task', task, 'var', 'disable_note', step=step, index=index)
    if no_note == ['true']:
        options.append('-nonote')

    return options
