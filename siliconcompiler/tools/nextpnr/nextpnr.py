'''
nextpnr is a vendor neutral FPGA place and route tool with
support for the ICE40, ECP5, and Nexus devices from Lattice.

Documentation: https://github.com/YosysHQ/nextpnr

Sources: https://github.com/YosysHQ/nextpnr

Installation: https://github.com/YosysHQ/nextpnr
'''


#####################################################################
# Make Docs
#####################################################################
def make_docs(chip):
    from siliconcompiler.tools.nextpnr.apr import setup
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

    partname = chip.get('fpga', 'partname')
    topmodule = chip.top()

    options = []

    options.extend(['--json', 'inputs/' + topmodule + '.netlist.json'])
    options.extend(['--asc', 'outputs/' + topmodule + '.asc'])

    if partname == 'ice40up5k-sg48':
        options.extend(['--up5k', '--package', 'sg48'])

    for constraint_file in chip.find_files('input', 'constraint', 'pcf', step=step, index=index):
        options.extend(['--pcf', constraint_file])

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
