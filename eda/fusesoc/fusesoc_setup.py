import glob
import os
import shutil
from siliconcompiler.schema import schema_path

################################
# Setup NextPNR
################################

def setup_tool(chip, step):
    ''' Sets up default settings on a per step basis
    '''

    refdir = 'eda/fusesoc'

    chip.add('flow', step, 'threads', '4')
    chip.add('flow', step, 'format', 'cmdline')
    chip.add('flow', step, 'vendor', 'fusesoc')
    chip.add('flow', step, 'refdir', refdir)
    chip.add('flow', step, 'exe', 'fusesoc')
    chip.add('flow', step, 'copy', 'false')

    # Check FPGA schema to determine which device to target
    if len(chip.get('fpga', 'vendor')) == 0 or len(chip.get('fpga', 'device')) == 0:
        chip.logger.error(f"FPGA device and/or vendor unspecified!")
        os.sys.exit()

    vendor = chip.get('fpga', 'vendor')[-1]
    device = chip.get('fpga', 'device')[-1]

    if vendor == 'lattice' and device == 'ice40up5k-sg48':
        options = '--up5k --package sg48'
    elif vendor == 'lattice' and device == 'ecp5-25k-285c':
        options = '--25k --package CSFBGA285'
    else:
        chip.logger.error(f"Unsupported vendor option '{vendor}' and device "
            f"option '{device}'.")
        os.sys.exit()

    chip.add('flow', step, 'option', options)

################################
# Set fusesoc Runtime Options
################################

def setup_options(chip, step):
    ''' Per tool/step function that returns a dynamic options string based on
    the dictionary settings.
    '''

    # Ensure that a constraint file was passed in.
    constraint_file = chip.get('constraint')[-1]
    if constraint_file == None:
        chip.logger.error('Pin constraint file required')
        os.sys.exit()

    # fusesoc has its own project structure, so we need to generate a
    # minimal project wrapper to run our FPGA design through it.
    topmodule = chip.get('design')[-1]
    device = chip.get('fpga', 'device')[-1]
    with open('fusesoc.conf', 'w') as f:
        f.write('[library.' + topmodule + ']\n')
        f.write('location = .\n')

    # Generate the fusesoc project config.
    constraint_file = chip.get('constraint')[-1]
    constraint_fn = constraint_file[constraint_file.rfind('/'):].lstrip('/')
    constraint_ext = constraint_file[constraint_file.rfind('.'):]
    constraint_type = constraint_ext[1:].upper()
    shutil.copy('../import/inputs/'+constraint_fn,
                'inputs/'+topmodule+constraint_ext)
    options_str = ', '.join(chip.get('flow', 'export', 'option'))
    chip.set('flow', 'export', 'option',
             ['run', '--target='+topmodule, 'sc:'+topmodule+':1.0'])
    if 'ice40' in device:
        device_tool = 'icestorm'
    elif 'ecp5' in device:
        device_tool = 'trellis'
    with open(topmodule + '.core', 'w') as f:
        f.write(\
f'''CAPI=2:
name: sc:{topmodule}:1.0

filesets:
  rtl:
    files:
      - inputs/{topmodule}.v
    file_type: verilogSource

  constraints:
    files:
      - inputs/{topmodule}{constraint_ext}
    file_type: {constraint_type}

targets:
  {topmodule}:
    default_tool: {device_tool}
    filesets: [rtl, constraints]
    tools:
      {device_tool}:
        nextpnr_options: [{options_str}]
    toplevel: {topmodule}
''')

    return chip.get('flow', 'export', 'option')

def pre_process(chip, step):
    ''' Tool specific function to run before step execution
    '''

    pass

def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''

    # Copy the bitstream file to the 'outputs/' directory.
    topmodule = chip.get('design')[-1]
    device = chip.get('fpga', 'device')[-1]
    if 'ice40' in device:
        ext = '.bin'
    elif 'ecp5' in device:
        ext = '.bit'
    bitstream_path = 'build/sc_'+topmodule+'_1.0_0/'+topmodule+'*/*'+ext
    for bitstream in glob.glob(bitstream_path):
        shutil.copy(bitstream, 'outputs/'+topmodule+ext)
