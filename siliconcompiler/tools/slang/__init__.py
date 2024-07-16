'''
slang is a software library that provides various components for lexing, parsing, type checking,
and elaborating SystemVerilog code. It comes with an executable tool that can compile and lint
any SystemVerilog project, but it is also intended to be usable as a front end for synthesis
tools, simulators, linters, code editors, and refactoring tools.

Documentation: https://sv-lang.com/

Sources: https://github.com/MikePopoloski/slang

Installation: https://sv-lang.com/building.html
'''
import re
from siliconcompiler import sc_open
from siliconcompiler.tools._common import get_tool_task, record_metric


################################
# Setup Tool (pre executable)
################################
def setup(chip):
    tool = 'slang'

    # Standard Setup
    chip.set('tool', tool, 'exe', 'slang')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=6.0', clobber=False)


def parse_version(stdout):
    # slang --version output looks like:
    # slang version 6.0.121+c2c478cf

    # grab version # by splitting on whitespace
    return stdout.strip().split()[-1].split('+')[0]


def post_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    log = f'{step}.log'
    with sc_open(log) as f:
        for line in f:
            match = re.search(r'(\d+) errors, (\d+) warnings', line)
            if match:
                record_metric(chip, step, index, 'errors', match.group(1), log)
                record_metric(chip, step, index, 'warnings', match.group(2), log)
