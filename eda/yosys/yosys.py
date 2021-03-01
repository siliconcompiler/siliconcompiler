
def setup_tool(chip, stage):

     refdir = 'eda/yosys'

     chip.add('tool', stage, 'threads', '4')
     chip.add('tool', stage, 'format', 'tcl')
     chip.add('tool', stage, 'copy', 'true')
     chip.add('tool', stage, 'vendor', 'yosys')
     chip.add('tool', stage, 'exe', 'yosys')
     chip.add('tool', stage, 'opt', '-c')
     chip.add('tool', stage, 'refdir', refdir)
     chip.add('tool', stage, 'script', refdir + '/sc_syn.tcl')
   
def setup_options(chip,stage):

     options = chip.get('tool', stage, 'opt')
     return options

################################
# Pre and Post Run Commands
################################
def pre_process(chip,stage):
    ''' Tool specific function to run before stage execution
    '''
    pass

def post_process(chip,stage):
    ''' Tool specific function to run after stage execution
    '''
    pass
