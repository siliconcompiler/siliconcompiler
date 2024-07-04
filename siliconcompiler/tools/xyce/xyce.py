'''
Xyce is a high performance SPICE-compatible circuit simulator
capable capable of solving extremely large circuit problems by
supporting large-scale parallel computing platforms. It also
supports serial execution on all common desktop platforms,
and small-scale parallel runs on Unix-like systems.

Documentation: https://xyce.sandia.gov/documentation-tutorials/

Sources: https://github.com/Xyce/Xyce

Installation: https://xyce.sandia.gov/documentation-tutorials/building-guide/

Status: SC integration WIP
'''

import os
from siliconcompiler.tools._common import get_tool_task


################################
# Setup Tool (pre executable)
################################
def setup(chip):

    tool = 'xyce'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    clobber = False

    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'version', '0.0', clobber=clobber)
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=clobber)
