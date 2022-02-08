import os
import shutil
import siliconcompiler

#####################################################################
# Make Docs
#####################################################################

def make_docs():
    '''
    GHDL is an open-source analyzer, compiler, simulator and
    (experimental) synthesizer for VHDL. It allows you to analyse
    and elaborate sources for generating machine code from your design.
    Native program execution is the only way for high speed simulation.

    Documentation: https://ghdl.readthedocs.io/en/latest

    Sources: https://github.com/ghdl/ghdl

    Installation: https://github.com/ghdl/ghdl

    '''

    chip = siliconcompiler.Chip()
    chip.set('arg','step','import')
    chip.set('arg','index','<index>')
    setup(chip)
    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings.
    '''

    # Standard Setup
    tool = 'ghdl'
    clobber = False

    step = chip.get('arg','step')
    index = chip.get('arg','index')

    chip.set('eda', tool, 'copy', 'false', clobber=clobber)
    chip.set('eda', tool, 'exe', 'ghdl', clobber=clobber)
    chip.set('eda', tool, 'vswitch', '--version', clobber=clobber)
    chip.set('eda', tool, 'version', '2.0.0-dev', clobber=clobber)
    chip.set('eda', tool, 'threads', step, index, '4', clobber=clobber)
    chip.set('eda', tool, 'option', step, index, '', clobber=clobber)

    # Schema requirements
    chip.add('eda', tool, 'require', step, index, 'source')

################################
#  Custom runtime options
################################

def runtime_options(chip):

    ''' Custom runtime options, returnst list of command line options.
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    options = []

    # Synthesize inputs and output Verilog netlist
    options.append('--synth')
    options.append('--out=verilog')

    # Add sources
    for value in chip.find_files('source'):
        options.append(value)

    # Set top module
    design = chip.get('design')
    options.append('-e')
    options.append(design)

    return options

################################
# Version Check
################################

def parse_version(stdout):
    # first line: GHDL 2.0.0-dev (1.0.0.r827.ge49cb7b9) [Dunoon edition]
    return stdout.split()[1]

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    # Hack: since ghdl outputs netlist to stdout, we produce the Verilog output
    # by copying the log.

    design = chip.get('design')
    step = chip.get('arg', 'step')
    infile = f'{step}.log'
    outfile = os.path.join('outputs', f'{design}.v')

    shutil.copyfile(infile, outfile)

    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup(chip, step='import', index='0')
    # write out results
    chip.writecfg(output)
