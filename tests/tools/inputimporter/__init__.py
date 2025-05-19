'''
This tool is used to copy files into the SiliconCompiler flow. It copies files
into the output directory to be absorbed into downstream nodes.
'''

from siliconcompiler.tools._common import get_tool_task


################################
# Setup Tool (pre executable)
################################
def setup(chip):
    tool = 'inputimporter'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    _, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'exe', 'cp')

    chip.set('tool', tool, 'task', task, 'regex', 'warnings', r'^\[WRN:',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'errors', r'^\[(ERR|FTL|SNT):',
             step=step, index=index, clobber=False)


################################
# Version Check
################################
def parse_version(stdout):
    raise IndexError('This is an index error')
