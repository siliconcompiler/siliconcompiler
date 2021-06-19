import os
from siliconcompiler.schema import schema_path

################################
# Setup NextPNR
################################

def setup_tool(chip, step):
    ''' Sets up default settings on a per step basis
    '''

    refdir = 'eda/nextpnr'

    vendor = chip.get('fpga', 'vendor')[-1]
    device = chip.get('fpga', 'device')[-1]

    chip.add('flow', step, 'threads', '4')
    chip.add('flow', step, 'format', 'cmdline')
    chip.add('flow', step, 'vendor', 'nextpnr')
    chip.add('flow', step, 'refdir', refdir)
    if 'ice40' in device:
        chip.add('flow', step, 'exe', 'nextpnr-ice40')
    elif 'ecp5' in device:
        chip.add('flow', step, 'exe', 'nextpnr-ecp5')
    chip.add('flow', step, 'copy', 'false')

    # Check FPGA schema to determine which device to target
    if len(chip.get('fpga', 'vendor')) == 0 or len(chip.get('fpga', 'device')) == 0:
        chip.logger.error(f"FPGA device and/or vendor unspecified!")
        os.sys.exit()

    if vendor == 'lattice' and device == 'ice40up5k-sg48':
        options = '--up5k --package sg48'
    elif vendor == 'lattice' and device == 'ecp5-25k-285c':
        options = '--25k --package CSFBGA285'
    else:
        chip.logger.error(f"Unsupported vendor option '{vendor}' and device option "
            f"'{device}'. NextPNR flow currently only supports a subset of lattice "
            f"iCE40 and ECP5 devices.")
        os.sys.exit()

    chip.add('flow', step, 'option', options)

################################
# Set NextPNR Runtime Options
################################

def setup_options(chip, step):
    ''' Per tool/step function that returns a dynamic options string based on
    the dictionary settings.
    '''

    #Get default opptions from setup
    options = chip.get('flow', step, 'option')

    topmodule = chip.get('design')[-1]
    device = chip.get('fpga', 'device')[-1]

    pcf_file = None
    for constraint_file in chip.get('constraint'):
        if os.path.splitext(constraint_file)[-1] == '.pcf':
            pcf_file = schema_path(constraint_file)

    if pcf_file == None:
        chip.logger.error('Pin constraint file required')
        os.sys.exit()

    if 'ice40' in device:
        options.append('--pcf ' + pcf_file)
        options.append('--asc outputs/' + topmodule + '.asc')
    elif 'ecp5' in device:
        options.append('--lpf ' + pcf_file)
        options.append('--textcfg outputs/' + topmodule + '.asc')
    options.append('--json inputs/' + topmodule + '_netlist.json')

    return options

def pre_process(chip, step):
    ''' Tool specific function to run before step execution
    '''
    pass

def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''
    pass
