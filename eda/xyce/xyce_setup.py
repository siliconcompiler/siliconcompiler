################################
# Tool Setup
################################

def setup_tool(chip, step):

     refdir = 'eda/xyce'

     chip.add('flow', step, 'threads', '4')
     chip.add('flow', step, 'format', 'cmdline')
     chip.add('flow', step, 'copy', 'false')
     chip.add('flow', step, 'vendor', 'xyce')
     chip.add('flow', step, 'exe', 'xyce')
     chip.add('flow', step, 'option', '')
     chip.add('flow', step, 'refdir', refdir)
   
def setup_options(chip, step):

     options = chip.get('flow', step, 'opt')
     return options

################################
# Pre and Post Run Commands
################################
def pre_process(chip, step):
    ''' Tool specific function to run before step execution
    '''
    pass

def post_process(chip, step, status):
    ''' Tool specific function to run after step execution
    '''

    #TODO: return error code
    return status
