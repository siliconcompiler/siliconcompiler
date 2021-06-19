import shutil
import subprocess

################################
# Setup ecppack
################################

def setup_tool(chip, step):
    ''' Sets up default settings on a per step basis
    '''

    chip.add('flow', step, 'threads', '4')
    chip.add('flow', step, 'format', 'cmdline')
    chip.add('flow', step, 'copy', 'false')
    chip.add('flow', step, 'vendor', 'ecppack')
    chip.add('flow', step, 'exe', 'ecppack')
    chip.add('flow', step, 'refdir', '')
    chip.add('flow', step, 'option', '')

################################
# Set ecppack Runtime Options
################################

def setup_options(chip, step):
    ''' Per step function that returns a dynamic options string based on
    the dictionary settings.
    '''

    #Get default opptions from setup
    options = chip.get('flow', step, 'option')

    topmodule = chip.get('design')[-1]

    options.append("inputs/" + topmodule + ".asc")
    options.append("outputs/" + topmodule + ".bit")

    return options

def pre_process(chip, step):
    ''' Tool specific function to run before step execution
    '''
    pass

def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''

    # Apply DFU suffix to the bitstream for USB uploading.
    topmodule = chip.get('design')[-1]
    dfu_fn = './outputs/' + topmodule + '.dfu'
    shutil.copyfile('./outputs/' + topmodule + '.bit', dfu_fn)
    subprocess.run(['dfu-suffix', '-v', '1209', '-p', '5af0', '-a', dfu_fn])
