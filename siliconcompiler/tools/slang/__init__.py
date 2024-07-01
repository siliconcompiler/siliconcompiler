'''
slang is a software library that provides various components for lexing, parsing, type checking,
and elaborating SystemVerilog code. It comes with an executable tool that can compile and lint
any SystemVerilog project, but it is also intended to be usable as a front end for synthesis
tools, simulators, linters, code editors, and refactoring tools.

Documentation: https://sv-lang.com/

Sources: https://github.com/MikePopoloski/slang

Installation: https://sv-lang.com/building.html
'''


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
