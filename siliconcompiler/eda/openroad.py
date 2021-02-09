
import os
import siliconcompiler as sc

def setup_openroad(chip, root):

     #local variables
     refdir = root + '/openroad'
     
     for stage in ('floorplan', 'place', 'cts', 'route', 'signoff'):
          chip.add('tool', stage, 'np', '4')
          chip.add('tool', stage, 'format', 'tcl')
          chip.add('tool', stage, 'copy', 'False')
          chip.add('tool', stage, 'vendor', 'openroad')
          chip.add('tool', stage, 'exe', 'openroad')
          chip.add('tool', stage, 'opt', '-no_init -exit')
          chip.add('tool', stage, 'refdir', refdir)
          chip.add('tool', stage, 'script', refdir + '/sc_'+stage+'.tcl')
