import glob
import os
import stat
from siliconcompiler.tools.execute.execute import setup as tool_setup
from siliconcompiler.tools.execute.execute import skip_checks as tool_skip_checks


def setup(chip):
    '''
    Execute the output of the previous step directly.
    This only works if the task recieves a single file.
    '''
    tool_setup(chip)


def pre_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, _ = chip._get_tool_task(step, index)

    exec = None
    for fin in glob.glob('inputs/*'):
        exec = os.path.abspath(fin)
        break

    if not exec:
        chip.error(f'{step}{index} did not receive an executable file')

    chip.set('tool', tool, 'exe', exec)

    os.chmod(exec, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


def skip_checks(chip):
    return tool_skip_checks(chip)
