'''
Xyce is a high performance SPICE-compatible circuit simulator
capable capable of solving extremely large circuit problems by
supporting large-scale parallel computing platforms. It also
supports serial execution on all common desktop platforms,
and small-scale parallel runs on Unix-like systems.

Documentation: https://xyce.sandia.gov/documentation-tutorials/

Sources: https://xyce.sandia.gov/downloads/source-code/

Installation: https://xyce.sandia.gov/documentation-tutorials/building-guide/

Status: SC integration WIP
'''
from siliconcompiler.tools._common import get_tool_task


################################
# Setup Tool (pre executable)
################################
def setup(chip):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'exe', 'Xyce')
    chip.set('tool', tool, 'vswitch', '-v')
    chip.set('tool', tool, 'version', '>=v7.8')

    chip.set('tool', tool, 'task', task, 'regex', 'warnings', 'warning',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'errors', 'error',
             step=step, index=index, clobber=False)


def parse_version(stdout):
    ver = stdout.split()[-1]
    return ver.split('-')[0]
