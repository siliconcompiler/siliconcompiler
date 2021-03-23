################################
# Tool Setup
################################

def setup_tool(chip, step, tool):

     refdir = 'eda/klayout'
     
     for step in (['export', 'gdsview']):
          chip.add('flow', step, 'threads', '4')
          chip.add('flow', step, 'format', 'json')
          chip.add('flow', step, 'copy', 'true')
          chip.add('flow', step, 'vendor', 'klayout')
          chip.add('flow', step, 'exe', 'klayout') 
          chip.add('flow', step, 'refdir', refdir)
          if step == 'gdsview':               
               chip.add('flow', step, 'opt', '-nn')
          elif step == 'export':               
               chip.add('flow', step, 'opt', '-rm')
          
def setup_options(chip,step , tool):
     
     options = chip.get('flow', step, 'opt')
     return options

################################
# Pre/Post Processing
################################
def pre_process(chip, step, tool):
    ''' Tool specific function to run before step execution
    '''
    pass

def post_process(chip, step, tool):
    ''' Tool specific function to run after step execution
    '''
    pass
