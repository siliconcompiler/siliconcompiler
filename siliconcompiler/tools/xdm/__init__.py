'''
Xyce XDM netlist converter, used to convert PSPICE and HSPICE netists into Xyce format.

Sources: https://github.com/Xyce/XDM

Installation: https://github.com/Xyce/XDM

Status: SC integration WIP
'''
from siliconcompiler.tools._common import get_tool_task


def setup(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'exe', 'xdm_bdl')
    chip.set('tool', tool, 'vswitch', '-h')
    chip.set('tool', tool, 'version', '>=v2.7.0', clobber=False)


################################
# Version Check
################################
def parse_version(stdout):
    line = stdout.splitlines()[5]
    return line.split()[1]
