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

    chip = siliconcompiler.Chip('<design>')
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

    chip.set('tool', tool, 'exe', 'ghdl')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=2.0.0-dev', clobber=clobber)
    chip.set('tool', tool, 'threads', step, index, '4', clobber=clobber)
    chip.set('tool', tool, 'option', step, index, '', clobber=clobber)
    chip.set('tool', tool, 'stdout', step, index, 'destination', 'output')
    chip.set('tool', tool, 'stdout', step, index, 'suffix', 'v')

    # Schema requirements
    chip.add('tool', tool, 'require', step, index, 'input,vhdl')

    design = chip.top()

    chip.set('tool', tool, 'output', step, index, f'{design}.v')

################################
#  Custom runtime options
################################

def runtime_options(chip):

    ''' Custom runtime options, returnst list of command line options.
    '''

    step = chip.get('arg','step')
    index = chip.get('arg','index')

    options = []

    # Synthesize inputs and output Verilog netlist
    options.append('--synth')
    options.append('--std=08')
    options.append('--out=verilog')
    options.append('--no-formal')

    if chip.valid('tool', 'ghdl', 'var', step, index, 'extraopts'):
        extra_opts = chip.get('tool', 'ghdl', 'var', step, index, 'extraopts')
        # currently only -fsynopsys supported
        for opt in extra_opts:
            if opt == '-fsynopsys':
                options.append(opt)
            else:
                chip.error('Unsupported option ' + opt)

    # Add sources
    for value in chip.find_files('input', 'vhdl'):
        options.append(value)

    # Set top module
    design = chip.top()
    options.append('-e')
    options.append(design)

    return options

################################
# Version Check
################################

def parse_version(stdout):
    # first line: GHDL 2.0.0-dev (1.0.0.r827.ge49cb7b9) [Dunoon edition]

    # '*-dev' is interpreted by packaging.version as a "developmental release",
    # which has the correct semantics. e.g. Version('2.0.0') > Version('2.0.0-dev')
    return stdout.split()[1]

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("ghdl.json")
