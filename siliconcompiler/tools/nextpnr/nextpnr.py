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
    setup_tool(chip)
    return chip

################################
# Setup NextPNR
################################

def setup_tool(chip):
    ''' Sets up default settings on a per step basis
    '''

    tool = 'nextpnr'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    clobber = False
    chip.set('eda', tool, step, index, 'exe', 'nextpnr-ice40', clobber=clobber)
    chip.set('eda', tool, step, index, 'vswitch', '--version', clobber=clobber)
    chip.set('eda', tool, step, index, 'version', 'c73d4cf6', clobber=clobber)
    chip.set('eda', tool, step, index, 'option', 'cmdline', "", clobber=clobber)

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

    pcf_file = None
    for constraint_file in chip.get('constraint'):
        if os.path.splitext(constraint_file)[-1] == '.pcf':
            pcf_file = chip.find_file(constraint_file)
            options.append('--pcf ' + pcf_file)

    return options

################################
# Version Check
################################

def check_version(chip, version):
    ''' Tool specific version checking
    '''
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    required = chip.get('eda', 'nextpnr', step, index, 'version')
    #insert code for parsing the funtion based on some tool specific
    #semantics.
    #syntax for version is string, >=string

    return 0

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
