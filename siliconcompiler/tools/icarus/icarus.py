
'''
Icarus is a verilog simulator with full support for Verilog
IEEE-1364. Icarus can simulate synthesizable as well as
behavioral Verilog.

Documentation: https://steveicarus.github.io/iverilog/

Sources: https://github.com/steveicarus/iverilog

Installation: https://github.com/steveicarus/iverilog
'''
from siliconcompiler.tools._common import get_key_files, get_key_values


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    from tools.icarus.compile import setup
    setup(chip)
    return chip


################################
#  Custom runtime options
################################
def runtime_options(chip):

    ''' Custom runtime options, returns list of command line options.
    '''

    cmdlist = []

    # source files
    for value in get_key_files(chip, 'option', 'ydir'):
        cmdlist.append('-y ' + value)
    for value in get_key_files(chip, 'option', 'vlib'):
        cmdlist.append('-v ' + value)
    for value in get_key_files(chip, 'option', 'idir'):
        cmdlist.append('-I' + value)
    for value in get_key_values(chip, 'option', 'define'):
        cmdlist.append('-D' + value)
    for value in get_key_files(chip, 'option', 'cmdfile'):
        cmdlist.append('-f ' + value)
    for value in get_key_files(chip, 'input', 'rtl', 'verilog'):
        cmdlist.append(value)

    return cmdlist


################################
# Version Check
################################
def parse_version(stdout):
    # First line: Icarus Verilog version 10.1 (stable) ()
    return stdout.split()[3]


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("icarus.json")
