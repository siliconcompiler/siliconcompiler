# Dummy tool for steps we skip

def setup_options(chip,step):
    ''' Per tool/step function that returns a dynamic options string based on
    the dictionary settings.
    '''
    return ["-r inputs/. outputs/"]

def pre_process(chip,step):
    ''' Tool specific function to run before step execution
    '''
    pass

def post_process(chip,step):
    ''' Tool specific function to run after step execution
    '''
    pass
