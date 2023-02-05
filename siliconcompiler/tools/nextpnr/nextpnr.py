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
    step = 'apr'
    index = '<index>'
    flow = '<flow>'
    chip.set('arg','step',step)
    chip.set('arg','index',index)
    chip.set('option', 'flow', flow)
    chip.set('flowgraph', flow, step, index, 'task', '<task>')
    from tools.nextpnr.apr import setup
    setup(chip)
    return chip

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

    for constraint_file in chip.find_files('input', 'fpga', 'pcf'):
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
