'''
OpenSTA is a gate level static timing verifier.

Documentation: https://github.com/The-OpenROAD-Project/OpenSTA/blob/master/doc/OpenSTA.pdf

Sources: https://github.com/The-OpenROAD-Project/OpenSTA

Installation: https://github.com/The-OpenROAD-Project/OpenSTA (also installed with OpenROAD)
'''

import os
from siliconcompiler.tools.openroad.openroad import get_library_timing_keypaths
from siliconcompiler.tools._common import get_tool_task
from siliconcompiler.tools._common.asic import get_libraries
from siliconcompiler.targets import asap7_demo


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    chip.use(asap7_demo)


################################
# Setup Tool (pre executable)
################################
def setup(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'exe', 'sta')
    chip.set('tool', tool, 'vswitch', '-version')
    chip.set('tool', tool, 'version', '>=v2.5.0', clobber=False)
    chip.set('tool', tool, 'format', 'tcl')

    targetlibs = get_libraries(chip, 'logic')
    macrolibs = get_libraries(chip, 'macro')
    delaymodel = chip.get('asic', 'delaymodel', step=step, index=index)

    # Input/Output requirements for default asicflow steps
    chip.set('tool', tool, 'task', task, 'refdir', 'tools/opensta/scripts',
             step=step, index=index,
             package='siliconcompiler', clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)

    if delaymodel != 'nldm':
        chip.logger.error(f'{delaymodel} delay model is not supported by {tool}, only nldm')

    if targetlibs:
        # Note: only one footprint supported in mainlib
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['asic', 'logiclib']),
                 step=step, index=index)

        for lib in targetlibs:
            for timing_key in get_library_timing_keypaths(chip, lib).values():
                chip.add('tool', tool, 'task', task, 'require', ",".join(timing_key),
                         step=step, index=index)
        for lib in macrolibs:
            for timing_key in get_library_timing_keypaths(chip, lib).values():
                if chip.valid(*timing_key):
                    chip.add('tool', tool, 'task', task, 'require', ",".join(timing_key),
                             step=step, index=index)
    else:
        chip.error('logiclib parameters required for OpenSTA.')

    # basic warning and error grep check on logfile
    chip.set('tool', tool, 'task', task, 'regex', 'warnings', r'^\[WARNING|^Warning',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'errors', r'^\[ERROR',
             step=step, index=index, clobber=False)


################################
# Version Check
################################
def parse_version(stdout):
    return stdout.strip()


################################
# Runtime options
################################
def runtime_options(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    # exit automatically in batch mode and not breakpoint
    option = []
    if not chip.get('option', 'breakpoint', step=step, index=index):
        option.append("-exit")

    tool, task = get_tool_task(chip, step, index)
    option.extend([
        '-threads',
        str(chip.get('tool', tool, 'task', task, 'threads', step=step, index=index))
    ])

    return option
