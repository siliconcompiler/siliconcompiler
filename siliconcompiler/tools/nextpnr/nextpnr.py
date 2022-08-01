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

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg','step','<apr>')
    chip.set('arg','index','<index>')
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
    chip.set('tool', tool, 'exe', 'nextpnr-ice40')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=0.2', clobber=clobber)
    chip.set('tool', tool, 'option', step, index, "", clobber=clobber)

    topmodule = chip.top()
    chip.set('tool', tool, 'input', step, index, f'{topmodule}_netlist.json')
    chip.set('tool', tool, 'output', step, index, f'{topmodule}.asc')

################################
#  Custom runtime options
################################

def runtime_options(chip):
    ''' Custom runtime options, returns list of command line options.
    '''

    partname = chip.get('fpga', 'partname')
    topmodule = chip.top()

    options = []

    options.append('--json inputs/' + topmodule + '_netlist.json')
    options.append('--asc outputs/' + topmodule + '.asc')

    if partname == 'ice40up5k-sg48':
        options.append('--up5k --package sg48')

    for constraint_file in chip.find_files('input', 'pcf'):
        options.append('--pcf ' + constraint_file)

    return options

################################
# Version Check
################################

def parse_version(stdout):
    # Examples:
    # nextpnr-ice40 -- Next Generation Place and Route (Version c73d4cf6)
    # nextpnr-ice40 -- Next Generation Place and Route (Version nextpnr-0.2)
    version = stdout.split()[-1].rstrip(')')
    if version.startswith('nextpnr-'):
        return version.split('-')[1]
    else:
        return version
