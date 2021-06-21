import glob
import os
import re
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

    # Find the directory containing the FPGA board files.
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    sc_root   = re.sub('siliconcompiler/eda/fusesoc',
                       'siliconcompiler',
                       scriptdir)
    board_loc = sc_root + '/fpga/boards/' + device

    # Copy the board's pin constraint file.
    constraint_file = chip.get('constraint')[-1]
    constraint_fn = constraint_file[constraint_file.rfind('/'):].lstrip('/')
    shutil.copy(board_loc + '/' + constraint_fn, 'inputs/' + constraint_fn)
    # Copy the source Verilog to the path expected by the fusesoc config.
    shutil.copy('inputs/'+topmodule+'.v', 'inputs/sc.v')
    # Copy the board's fusesoc config and append the top-level module's name.
    shutil.copy(board_loc + '/' + device + '.core', device + '.core')
    with open(device + '.core', 'a') as f:
      f.write('\n    toplevel: ' + topmodule + '\n')

    # Generate and return the run command.
    chip.set('flow', 'export', 'option', ['run', 'sc:'+device+':1.0'])
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
    bitstream_path = 'build/sc_*_1.0_0/default-*/*.bi[tn]'
    for bitstream in glob.glob(bitstream_path):
        shutil.copy(bitstream, 'outputs/'+topmodule+'.bit')
