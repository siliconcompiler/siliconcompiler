import os
import siliconcompiler
from siliconcompiler.schema_utils import schema_path


#####################################################################
# Make Docs
#####################################################################

def make_docs():
    '''nextpnr is a vendor neutral FPGA place and route tool

    Currently nextpnr supports:

    * Lattice ICE40 devices supported by Project IceStorm
    * Lattice ECP5 devices supported by Project Trellis
    * Lattice Nexus devices supported by Project Oxide
    * Gowin LittleBee devices supported by Project Apicula

    Documentation:
    * https://github.com/YosysHQ/nextpnr

    Build instructions:

    git clone https://github.com/YosysHQ/nextpnr nextpnr
    cd nextpnr
    cmake -DARCH=ice40 -DCMAKE_INSTALL_PREFIX=/usr/local .
    make -j$(nproc)
    sudo make install

    '''

    chip = siliconcompiler.Chip()
    setup_tool(chip, '<step>', '<index>')
    return chip

################################
# Setup NextPNR
################################

def setup_tool(chip, step, index):
    ''' Sets up default settings on a per step basis
    '''

    tool = 'nextpnr'
    clobber = False
    chip.set('eda', tool, step, index, 'exe', 'nextpnr-ice40', clobber=clobber)
    chip.set('eda', tool, step, index, 'vswitch', '--version', clobber=clobber)
    chip.set('eda', tool, step, index, 'version', 'c73d4cf6', clobber=clobber)

    # Check FPGA schema to determine which device to target
    partname = chip.get('fpga', 'partname')

    options = []
    if partname == 'ice40up5k-sg48':
        options.append('--up5k --package sg48')

    topmodule = chip.get('design')
    pcf_file = None
    for constraint_file in chip.get('constraint'):
        if os.path.splitext(constraint_file)[-1] == '.pcf':
            pcf_file = schema_path(constraint_file)
            options.append('--pcf ' + pcf_file)

    options.append('--json inputs/' + topmodule + '_netlist.json')
    options.append('--asc outputs/' + topmodule + '.asc')
    chip.add('eda', tool, step, index, 'option', 'cmdline', options)

################################
# Version Check
################################

def check_version(chip, step, index, version):
    ''' Tool specific version checking
    '''
    required = chip.get('eda', 'nextpnr', step, index, 'version')
    #insert code for parsing the funtion based on some tool specific
    #semantics.
    #syntax for version is string, >=string

    return 0

################################
# Setup Tool (pre executable)
################################

def post_process(chip, step, index):
    ''' Tool specific function to run after step execution
    '''
    #TODO: return error code
    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    chip.set('fpga', 'partname', 'ice40up5k-sg48')
    # load configuration
    setup_tool(chip, step='syn', index='0')
    # write out results
    chip.writecfg(output)
