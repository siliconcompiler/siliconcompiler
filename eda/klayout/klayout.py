
def setup_tool(chip, step):

     refdir = 'eda/klayout'
     
     for stage in (['export', 'gdsview']):
          chip.add('flow', stage, 'threads', '4')
          chip.add('flow', stage, 'format', 'json')
          chip.add('flow', stage, 'copy', 'true')
          chip.add('flow', stage, 'vendor', 'klayout')
          chip.add('flow', stage, 'exe', 'klayout') 
          chip.add('flow', stage, 'refdir', refdir)
          if stage == 'gdsview':               
               chip.add('flow', stage, 'opt', '-nn')
          elif stage == 'export':               
               chip.add('flow', stage, 'opt', '-rm')
          


def setup_options(chip,stage):
     
     options = chip.get('flow', stage, 'opt')
     return options
