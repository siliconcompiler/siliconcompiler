
def setup_openroad(chip):

     #local variables
     refdir = 'eda/openroad'
     
     for stage in ('floorplan', 'place', 'cts', 'route', 'signoff'):
          chip.add('tool', stage, 'threads', '4')
          chip.add('tool', stage, 'format', 'tcl')
          chip.add('tool', stage, 'copy', 'true')
          chip.add('tool', stage, 'vendor', 'openroad')
          chip.add('tool', stage, 'exe', 'openroad')
          chip.add('tool', stage, 'opt', '-no_init -exit')
          chip.add('tool', stage, 'refdir', refdir)
          chip.add('tool', stage, 'script', refdir + '/sc_'+stage+'.tcl')
