
'''
Icarus is a verilog simulator with full support for Verilog
IEEE-1364. Icarus can simulate synthesizable as well as
behavioral Verilog.

Documentation: https://steveicarus.github.io/iverilog/

Sources: https://github.com/steveicarus/iverilog

Installation: https://github.com/steveicarus/iverilog
'''


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

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    cmdlist = []

    # source files
    for value in chip.find_files('option', 'ydir'):
        cmdlist.append('-y ' + value)
    for value in chip.find_files('option', 'vlib'):
        cmdlist.append('-v ' + value)
    for value in chip.find_files('option', 'idir'):
        cmdlist.append('-I' + value)
    for value in chip.get('option', 'define'):
        cmdlist.append('-D' + value)
    for value in chip.find_files('option', 'cmdfile'):
        cmdlist.append('-f ' + value)
    for value in chip.find_files('input', 'rtl', 'verilog', step=step, index=index):
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
