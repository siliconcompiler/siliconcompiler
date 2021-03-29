################################
# Tool Setup
################################

def setup_tool(chip, step):

     #Shared setting for all openroad tools
     refdir = 'eda/openroad'
     chip.add('flow', step, 'threads', '4')
     chip.add('flow', step, 'copy', 'true')
     chip.add('flow', step, 'refdir', refdir)
     chip.add('flow', step, 'script', refdir + '/sc_'+step+'.tcl')
     
     chip.add('flow', step, 'format', 'tcl')
     chip.add('flow', step, 'vendor', 'openroad')
     chip.add('flow', step, 'exe', 'openroad')
     chip.add('flow', step, 'option', '-no_init -exit')

def setup_options(chip, step):

     options = chip.get('flow', step, 'option')
     return options
  
################################
# Pre/Post Processing
################################

def pre_process(chip, step):
    ''' Tool specific function to run before step execution
    '''
    pass

def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''
    pass
