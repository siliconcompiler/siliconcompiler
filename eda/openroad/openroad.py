
def setup_tool(chip, step):

     #local variables
     refdir = 'eda/openroad'
     
     chip.add('flow', step, 'threads', '4')
     chip.add('flow', step, 'format', 'tcl')
     chip.add('flow', step, 'copy', 'true')
     chip.add('flow', step, 'vendor', 'openroad')
     chip.add('flow', step, 'exe', 'openroad')
     chip.add('flow', step, 'opt', '-no_init -exit')
     chip.add('flow', step, 'refdir', refdir)
     chip.add('flow', step, 'script', refdir + '/sc_'+step+'.tcl')


def setup_options(chip,step):

     options = chip.get('flow', step, 'opt')
     return options
  
################################
# Pre and Post Run Commands
################################
def pre_process(chip,step):
    ''' Tool specific function to run before step execution
    '''
    pass

def post_process(chip,step):
    ''' Tool specific function to run after step execution
    '''
    pass
