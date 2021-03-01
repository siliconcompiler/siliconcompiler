
def setup_tool(chip, stage):

     refdir = 'eda/klayout'
     
     for stage in (['export', 'gdsview']):
          chip.add('tool', stage, 'threads', '4')
          chip.add('tool', stage, 'format', 'json')
          chip.add('tool', stage, 'copy', 'true')
          chip.add('tool', stage, 'vendor', 'klayout')
          chip.add('tool', stage, 'exe', 'klayout') 
          chip.add('tool', stage, 'refdir', refdir)
          if stage == 'gdsview':               
               chip.add('tool', stage, 'opt', '-nn')
          elif stage == 'export':               
               chip.add('tool', stage, 'opt', '-rm')
          


def setup_options(chip,stage):
     
     options = chip.get('tool', stage, 'opt')
     return options
