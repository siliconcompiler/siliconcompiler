
'''
GHDL is an open-source analyzer, compiler, simulator and
(experimental) synthesizer for VHDL. It allows you to analyse
and elaborate sources for generating machine code from your design.
Native program execution is the only way for high speed simulation.

Documentation: https://ghdl.readthedocs.io/en/latest

Sources: https://github.com/ghdl/ghdl

Installation: https://github.com/ghdl/ghdl
'''

from siliconcompiler.tools.ghdl import convert


#####################################################################
# Make Docs
#####################################################################
def make_docs(chip):
    convert.setup(chip)
    return chip


################################
#  Custom runtime options
################################
def runtime_options(chip):

    ''' Custom runtime options, returnst list of command line options.
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    options = []

    # Synthesize inputs and output Verilog netlist
    options.append('--synth')
    options.append('--std=08')
    options.append('--out=verilog')
    options.append('--no-formal')

    # currently only -fsynopsys and --latches supported
    valid_extraopts = ['-fsynopsys', '--latches']

    extra_opts = chip.get('tool', 'ghdl', 'task', task, 'var', 'extraopts', step=step, index=index)
    for opt in extra_opts:
        if opt in valid_extraopts:
            options.append(opt)
        else:
            chip.error('Unsupported option ' + opt)

    # Add sources
    for value in chip.find_files('input', 'rtl', 'vhdl', step=step, index=index):
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
