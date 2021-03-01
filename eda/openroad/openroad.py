
def setup_tool(chip,stage):

     #local variables
     refdir = 'eda/openroad'
     
     chip.add('tool', stage, 'threads', '4')
     chip.add('tool', stage, 'format', 'tcl')
     chip.add('tool', stage, 'copy', 'true')
     chip.add('tool', stage, 'vendor', 'openroad')
     chip.add('tool', stage, 'exe', 'openroad')
     chip.add('tool', stage, 'opt', '-no_init -exit')
     chip.add('tool', stage, 'refdir', refdir)
     chip.add('tool', stage, 'script', refdir + '/sc_'+stage+'.tcl')


def setup_options(chip,stage):

     options = chip.get('tool', stage, 'opt')
     return options
  
