################################
# Set NextPNR Runtime Options
################################

def setup_options(chip,step):
    ''' Per tool/step function that returns a dynamic options string based on
    the dictionary settings.
    '''

    #Get default opptions from setup
    options = chip.get('flow', step, 'opt')

    topmodule = chip.get('design')[-1]

    options.append("--json inputs/" + topmodule + ".json")
    options.append("--asc outputs/" + topmodule + ".asc")

    return options

def pre_process(chip,step):
    ''' Tool specific function to run before step execution
    '''
    pass

def post_process(chip,step):
    ''' Tool specific function to run after step execution
    '''
    pass
