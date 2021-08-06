import os
from siliconcompiler.schema import schema_path

################################
# Setup NextPNR
################################

def setup_tool(chip, step):
    ''' Sets up default settings on a per step basis
    '''

    refdir = 'siliconcompiler/tools/nextpnr'
    tool = 'nextpnr'
    chip.add('eda', tool, step, 'threads', '4')
    chip.add('eda', tool, step, 'format', 'cmdline')
    chip.add('eda', tool, step, 'vendor', 'nextpnr')
    chip.add('eda', tool, step, 'refdir', refdir)
    chip.add('eda', tool, step, 'copy', 'false')
    chip.add('eda',tool, step, 'exe', 'nextpnr-ice40')
    
    # Check FPGA schema to determine which device to target
    if len(chip.get('fpga', 'partname')) == 0:
        chip.logger.error(f"FPGA partname unspecified!")
        os.sys.exit()
    else:
        partname = chip.get('fpga', 'partname')[-1]


    options = []
    if partname == 'ice40up5k-sg48':
        options.append('--up5k --package sg48')
    else:
        chip.logger.error(f"Unsupported vendor option '{vendor}' and device option "
            f"'{device}'. NextPNR flow currently only supports vendor 'lattice' and device "
            f"'ice40up5k-sg48'.")
        os.sys.exit()

    topmodule = chip.get('design')[-1]
    pcf_file = None
    for constraint_file in chip.get('constraint'):
        if os.path.splitext(constraint_file)[-1] == '.pcf':
            pcf_file = schema_path(constraint_file)
            
    if pcf_file == None:
        chip.logger.error('Pin constraint file required')
        os.sys.exit()

    topmodule = chip.get('design')[-1]
    options.append('--pcf ' + pcf_file)
    options.append('--json inputs/' + topmodule + '_netlist.json')
    options.append('--asc outputs/' + topmodule + '.asc')
    chip.add('eda', tool, step, 'option', options)
    
################################
# Setup Tool (pre executable)
################################

def post_process(chip, step):
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
    chip = siliconcompiler.Chip(defaults=False)
    # load configuration
    setup_tool(chip, step='syn')
    # write out results
    chip.writecfg(output)
