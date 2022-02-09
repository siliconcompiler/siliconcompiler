import os
import siliconcompiler

#####################################################################
# Make Docs
#####################################################################

def make_docs():
    '''
    nextpnr is a vendor neutral FPGA place and route tool with
    support for the ICE40, ECP5, and Nexus devices from Lattice.

    Documentation: https://github.com/YosysHQ/nextpnr

    Sources: https://github.com/YosysHQ/nextpnr

    Installation: https://github.com/YosysHQ/nextpnr

    '''

    chip = siliconcompiler.Chip()
    chip.set('arg','step','<apr>')
    chip.set('arg','index','<index>')
    chip.set('design','<design>')
    setup(chip)
    return chip

################################
# Setup NextPNR
################################

def setup(chip):
    ''' Sets up default settings on a per step basis
    '''

    tool = 'nextpnr'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    clobber = False
    chip.set('eda', tool, 'exe', 'nextpnr-ice40', clobber=clobber)
    chip.set('eda', tool, 'vswitch', '--version', clobber=clobber)
    chip.set('eda', tool, 'version', 'c73d4cf6', clobber=clobber)
    chip.set('eda', tool, 'option', step, index, "", clobber=clobber)

    topmodule = chip.get('design')
    chip.set('eda', tool, 'input', step, index, f'{topmodule}_netlist.json')
    chip.set('eda', tool, 'output', step, index, f'{topmodule}.asc')

################################
#  Custom runtime options
################################

def runtime_options(chip):
    ''' Custom runtime options, returnst list of command line options.
    '''

    step = chip.get('arg','step')
    index = chip.get('arg','index')

    partname = chip.get('fpga', 'partname')
    topmodule = chip.get('design')

    options = []

    options.append('--json inputs/' + topmodule + '_netlist.json')
    options.append('--asc outputs/' + topmodule + '.asc')

    if partname == 'ice40up5k-sg48':
        options.append('--up5k --package sg48')

    for constraint_file in chip.find_files('constraint'):
        if os.path.splitext(constraint_file)[-1] == '.pcf':
            options.append('--pcf ' + constraint_file)

    return options

################################
# Version Check
################################

def parse_version(stdout):
    # nextpnr-ice40 -- Next Generation Place and Route (Version c73d4cf6)
    return stdout.split()[-1].rstrip(')')

################################
# Setup Tool (pre executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    #TODO: return error code
    return 0
