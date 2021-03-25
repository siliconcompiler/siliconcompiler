################################
# Setup icepack
################################

def setup_tool(chip, step, tool):
    ''' Sets up default settings on a per step basis
    '''

    chip.add('flow', step, 'threads', '4')
    chip.add('flow', step, 'format', 'cmdline')
    chip.add('flow', step, 'copy', 'false')
    chip.add('flow', step, 'vendor', 'icepack')
    chip.add('flow', step, 'exe', 'icepack')
    chip.add('flow', step, 'refdir', '')
    chip.add('flow', step, 'option', '')

################################
# Set icepack Runtime Options
################################

def setup_options(chip, step, tool):
    ''' Per tool/step function that returns a dynamic options string based on
    the dictionary settings.
    '''

    #Get default opptions from setup
    options = chip.get('flow', step, 'option')

    topmodule = chip.get('design')[-1]

    options.append("inputs/" + topmodule + ".asc")
    options.append("outputs/" + topmodule + ".bit")

    return options

def pre_process(chip, step, tool):
    ''' Tool specific function to run before step execution
    '''
    pass

def post_process(chip, step, tool):
    ''' Tool specific function to run after step execution
    '''
    pass
