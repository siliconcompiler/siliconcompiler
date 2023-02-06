import siliconcompiler

####################################################################
# Make Docs
####################################################################

def make_docs():
    '''
    Icarus is a verilog simulator with full support for Verilog
    IEEE-1364. Icarus can simulate synthesizable as well as
    behavioral Verilog.

    Documentation: http://iverilog.icarus.com

    Sources: https://github.com/steveicarus/iverilog.git

    Installation: https://github.com/steveicarus/iverilog.git

    '''

    chip = siliconcompiler.Chip('<design>')
    step = 'compile'
    index = '<index>'
    flow = '<flow>'
    chip.set('arg','step',step)
    chip.set('arg','index',index)
    chip.set('option', 'flow', flow)
    chip.set('flowgraph', flow, step, index, 'task', '<task>')
    from tools.icarus.compile import setup
    setup(chip)
    return chip

################################
#  Custom runtime options
################################

def runtime_options(chip):

    ''' Custom runtime options, returnst list of command line options.
    '''

    cmdlist = []

    # source files
    for value in chip.find_files('option','ydir'):
        cmdlist.append('-y ' + value)
    for value in chip.find_files('option','vlib'):
        cmdlist.append('-v ' + value)
    for value in chip.find_files('option','idir'):
        cmdlist.append('-I' + value)
    for value in chip.get('option','define'):
        cmdlist.append('-D' + value)
    for value in chip.find_files('option','cmdfile'):
        cmdlist.append('-f ' + value)
    for value in chip.find_files('input', 'rtl', 'verilog'):
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
